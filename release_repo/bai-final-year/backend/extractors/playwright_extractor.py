import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _normalize_domain_to_url(domain: str) -> str:
    domain = (domain or "").strip()
    if not domain:
        raise ValueError("domain is required")
    if domain.startswith('http://') or domain.startswith('https://'):
        return domain
    return f'https://{domain}'


def get_skeleton(domain: str, redis_client: Any) -> Optional[Dict]:
    """Return skeleton dict for domain, using Redis cache with 24h TTL."""
    key = f"skeleton:{domain}"
    try:
        cached = None
        if redis_client is not None:
            try:
                cached = redis_client.get(key)
            except Exception:
                logger.exception("Redis GET failed")

        if cached:
            try:
                return json.loads(cached)
            except Exception:
                logger.exception("Failed to decode cached skeleton")

        try:
            url = _normalize_domain_to_url(domain)
        except ValueError:
            logger.warning("Cannot build skeleton for empty domain")
            return None
        skeleton = {}

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
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

        if skeleton and redis_client is not None:
            try:
                redis_client.set(key, json.dumps(skeleton), ex=86400)
            except Exception:
                logger.exception("Failed to cache skeleton")

        return skeleton
    except Exception as e:
        logger.exception("get_skeleton failure: %s", e)
        return None
