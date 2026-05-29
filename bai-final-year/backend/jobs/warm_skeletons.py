import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, List
import os

try:
    import redis
except ImportError:
    redis = None

try:
    from ..extractors.playwright_extractor import get_skeleton
except ImportError:
    from extractors.playwright_extractor import get_skeleton

logger = logging.getLogger(__name__)


def _get_redis_client() -> Any:
    if redis is None:
        raise RuntimeError("redis package is required to warm skeletons")
    return redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', 6379)), db=0)


def _warm_domain(domain: str, redis_client: Any, retries: int = 2) -> bool:
    attempt = 0
    while attempt <= retries:
        try:
            skeleton = get_skeleton(domain, redis_client)
            if skeleton:
                logger.info("Warmed skeleton for %s (sections=%d)", domain, len(skeleton))
                return True
            else:
                logger.warning("Playwright extractor returned no skeleton for %s (attempt %d)", domain, attempt)
        except Exception:
            logger.exception("Error warming domain %s (attempt %d)", domain, attempt)
        attempt += 1
        time.sleep(1 + attempt)
    logger.error("Failed to warm skeleton for %s after %d attempts", domain, retries)
    return False


def warm_domains(domains: List[str], concurrency: int = 2, retries: int = 2):
    redis_client = _get_redis_client()
    results = {}
    if not domains:
        return results
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        future_map = {ex.submit(_warm_domain, d, redis_client, retries): d for d in domains}
        for fut in as_completed(future_map):
            d = future_map[fut]
            try:
                ok = fut.result()
                results[d] = ok
            except Exception:
                logger.exception("Unhandled error warming %s", d)
                results[d] = False
    return results


def warm_domains_in_background(domains: List[str], concurrency: int = 2, retries: int = 2):
    thread = threading.Thread(target=warm_domains, args=(domains, concurrency, retries), daemon=True)
    thread.start()
    return thread
