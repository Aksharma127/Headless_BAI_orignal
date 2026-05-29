import json
import logging
import os
import re
import selectors
import subprocess
import tempfile
import time
import hashlib
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


SKELETON_CACHE_TTL_SECONDS = int(os.getenv("SKELETON_CACHE_TTL_SECONDS", "86400"))
EXTRACTOR_LOCK_KEY = os.getenv("EXTRACTOR_LOCK_KEY", "bai:chromium_extractor_lock")
EXTRACTOR_LOCK_TTL_SECONDS = int(os.getenv("EXTRACTOR_LOCK_TTL_SECONDS", "120"))
EXTRACTOR_LOCK_WAIT_SECONDS = int(os.getenv("EXTRACTOR_LOCK_WAIT_SECONDS", "90"))
CUSTOM_CHROME_BINARY = os.getenv("BAI_CHROME_BINARY", "").strip()
USE_NATIVE_CHROME = os.getenv("BAI_USE_NATIVE_CHROME", "auto").lower()
NATIVE_CHROME_TIMEOUT_SECONDS = int(os.getenv("BAI_CHROME_TIMEOUT_SECONDS", "25"))
BAI_MARKER_PATTERN = re.compile(
    r"=== BAI_SKELETON_START ===\s*(\{.*?\})\s*=== BAI_SKELETON_END ===",
    flags=re.DOTALL,
)


def _normalize_domain_to_url(domain: str) -> str:
    domain = (domain or "").strip()
    if not domain:
        raise ValueError("domain is required")
    if domain.startswith('http://') or domain.startswith('https://'):
        return domain
    return f'https://{domain}'


def _cache_key(url: str) -> str:
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
    return f"skeleton:{url_hash}"


def _redis_get_json(redis_client: Any, key: str) -> Optional[Dict]:
    if redis_client is None:
        return None
    try:
        cached = redis_client.get(key)
    except Exception:
        logger.exception("Redis GET failed for %s", key)
        return None
    if not cached:
        return None
    try:
        if isinstance(cached, bytes):
            cached = cached.decode("utf-8")
        return json.loads(cached)
    except Exception:
        logger.exception("Failed to decode cached skeleton for %s", key)
        return None


def _redis_set_json(redis_client: Any, key: str, value: Dict) -> None:
    if redis_client is None or not value:
        return
    try:
        redis_client.set(key, json.dumps(value), ex=SKELETON_CACHE_TTL_SECONDS)
    except Exception:
        logger.exception("Failed to cache skeleton for %s", key)


def _acquire_extractor_lock(redis_client: Any) -> Optional[str]:
    """Serialize native/headless extraction so small cloud boxes do not OOM."""
    if redis_client is None:
        return None

    token = f"{os.getpid()}:{time.time_ns()}"
    deadline = time.monotonic() + EXTRACTOR_LOCK_WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            acquired = redis_client.set(
                EXTRACTOR_LOCK_KEY,
                token,
                nx=True,
                ex=EXTRACTOR_LOCK_TTL_SECONDS,
            )
            if acquired:
                return token
        except Exception:
            logger.exception("Redis lock acquisition failed; continuing without lock")
            return None
        time.sleep(0.25)

    raise TimeoutError(f"Timed out waiting for extractor lock {EXTRACTOR_LOCK_KEY}")


def _release_extractor_lock(redis_client: Any, token: Optional[str]) -> None:
    if redis_client is None or token is None:
        return
    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    end
    return 0
    """
    try:
        redis_client.eval(script, 1, EXTRACTOR_LOCK_KEY, token)
    except Exception:
        logger.exception("Redis lock release failed")


def _normalize_native_payload(payload: Dict) -> Dict:
    """Convert C++ marker JSON into the mapper's x_min/y_min schema."""
    if not payload:
        return {}

    if all(isinstance(value, dict) and "x_min" in value for value in payload.values()):
        return payload

    nodes = payload.get("sections") or payload.get("nodes") or []
    skeleton: Dict[str, Dict[str, float]] = {}
    section_index = 1
    for node in nodes:
        name = str(node.get("name", "")).lower()
        node_id = str(
            node.get("id")
            or node.get("section_id")
            or node.get("semantic_id")
            or ""
        ).strip()
        is_section = name in {"section", "footer"} or bool(node_id)
        if not is_section:
            continue
        try:
            x = float(node.get("x", node.get("x_min", 0)))
            y = float(node.get("y", node.get("y_min", 0)))
            width = float(node.get("width", node.get("x_max", x) - x))
            height = float(node.get("height", node.get("y_max", y) - y))
        except Exception:
            continue
        if width <= 0 or height <= 0:
            continue

        key = node_id or f"section_{section_index}"
        section_index += 1
        skeleton[key] = {
            "x_min": x,
            "y_min": y,
            "x_max": x + width,
            "y_max": y + height,
        }
    return skeleton


def _extract_marker_payload(output: str) -> Optional[Dict]:
    matches = BAI_MARKER_PATTERN.findall(output)
    if not matches:
        return None
    try:
        return json.loads(matches[-1].strip())
    except Exception:
        logger.exception("Native Chromium emitted invalid BAI skeleton JSON")
        return None


def _should_use_native_chrome() -> bool:
    if USE_NATIVE_CHROME in {"1", "true", "yes", "force"}:
        return bool(CUSTOM_CHROME_BINARY)
    if USE_NATIVE_CHROME in {"0", "false", "no", "off"}:
        return False
    return bool(CUSTOM_CHROME_BINARY and os.path.exists(CUSTOM_CHROME_BINARY))


def _extract_with_native_chromium(url: str) -> Optional[Dict]:
    if not _should_use_native_chrome():
        return None
    if not os.path.exists(CUSTOM_CHROME_BINARY):
        logger.warning("BAI_CHROME_BINARY does not exist: %s", CUSTOM_CHROME_BINARY)
        return None

    user_data_dir = tempfile.mkdtemp(prefix="bai-chrome-profile-")
    command = [
        CUSTOM_CHROME_BINARY,
        "--headless=new",
        "--enable-bai-telemetry",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-background-networking",
        "--disable-extensions",
        "--disable-sync",
        "--no-first-run",
        "--no-default-browser-check",
        "--no-sandbox",
        "--window-size=1920,1080",
        f"--user-data-dir={user_data_dir}",
        "--virtual-time-budget=5000",
        "--dump-dom",
        url,
    ]
    env = os.environ.copy()
    env.setdefault("FONTCONFIG_PATH", "/etc/fonts")
    env.setdefault("XDG_CACHE_HOME", "/tmp/bai-font-cache")
    env.setdefault("LD_LIBRARY_PATH", os.path.dirname(CUSTOM_CHROME_BINARY))

    process = None
    output_parts: list[str] = []
    returncode = None
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        selector = selectors.DefaultSelector()
        if process.stdout is not None:
            selector.register(process.stdout, selectors.EVENT_READ)
        if process.stderr is not None:
            selector.register(process.stderr, selectors.EVENT_READ)

        deadline = time.monotonic() + NATIVE_CHROME_TIMEOUT_SECONDS
        parsed_markers = 0
        while time.monotonic() < deadline:
            for key, _ in selector.select(timeout=0.25):
                chunk = key.fileobj.readline()
                if not chunk:
                    try:
                        selector.unregister(key.fileobj)
                    except Exception:
                        pass
                    continue
                output_parts.append(chunk)
                recent_output = "".join(output_parts)
                marker_count = recent_output.count("=== BAI_SKELETON_END ===")
                if marker_count > parsed_markers:
                    parsed_markers = marker_count
                    payload = _extract_marker_payload(recent_output)
                    skeleton = _normalize_native_payload(payload) if payload else {}
                    if not skeleton:
                        continue
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    returncode = process.returncode
                    return skeleton

            returncode = process.poll()
            if returncode is not None:
                break

        if process.poll() is None:
            process.kill()
            logger.warning("Native Chromium timed out while extracting %s", url)
    except Exception:
        logger.exception("Native Chromium launch failed for %s", url)
        return None
    finally:
        if process and process.poll() is None:
            process.kill()
        try:
            import shutil

            shutil.rmtree(user_data_dir, ignore_errors=True)
        except Exception:
            logger.debug("Failed to remove Chromium temp profile", exc_info=True)

    output = "".join(output_parts)
    payload = _extract_marker_payload(output)
    if not payload:
        logger.warning(
            "Native Chromium produced no BAI skeleton markers for %s rc=%s stderr_tail=%s",
            url,
            returncode,
            output[-500:],
        )
        return None
    return _normalize_native_payload(payload)


def _extract_with_playwright(url: str) -> Optional[Dict]:
    skeleton = {}
    from playwright.sync_api import sync_playwright

    launch_kwargs = {"headless": True}
    if CUSTOM_CHROME_BINARY and os.path.exists(CUSTOM_CHROME_BINARY):
        launch_kwargs["executable_path"] = CUSTOM_CHROME_BINARY
        launch_kwargs["args"] = [
            "--enable-bai-telemetry",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--window-size=1920,1080",
        ]

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        try:
            page.goto(url, timeout=15000, wait_until='domcontentloaded')
        except Exception:
            logger.exception("Playwright failed to load %s", url)
            browser.close()
            return None

        sections = page.query_selector_all('section')
        for el in sections:
            try:
                sid = el.get_attribute('id') or ''
                bbox = el.bounding_box()
                if not bbox:
                    continue
                x_min = bbox['x']
                y_min = bbox['y']
                x_max = bbox['x'] + bbox['width']
                y_max = bbox['y'] + bbox['height']
                key_id = sid if sid else f'section_{len(skeleton)+1}'
                skeleton[key_id] = {"x_min": x_min, "y_min": y_min, "x_max": x_max, "y_max": y_max}
            except Exception:
                logger.exception("Failed to process a section element")

        browser.close()
    return skeleton


def get_skeleton(domain: str, redis_client: Any) -> Optional[Dict]:
    """Return skeleton dict for domain, using Redis cache and one-at-a-time extraction."""
    try:
        try:
            url = _normalize_domain_to_url(domain)
        except ValueError:
            logger.warning("Cannot build skeleton for empty domain")
            return None

        key = _cache_key(url)
        cached = _redis_get_json(redis_client, key)
        if cached:
            return cached

        lock_token = _acquire_extractor_lock(redis_client)
        try:
            cached = _redis_get_json(redis_client, key)
            if cached:
                return cached

            skeleton = _extract_with_native_chromium(url)
            if not skeleton:
                skeleton = _extract_with_playwright(url) or {}
            _redis_set_json(redis_client, key, skeleton)
        finally:
            _release_extractor_lock(redis_client, lock_token)

        return skeleton
    except Exception as e:
        logger.exception("get_skeleton failure: %s", e)
        return None
