import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# Lazy imports: these are heavy dependencies that may not be available in all
# environments (e.g. CI with DEMO_MODE=true). Import failures are caught at
# function call time, not at module import time, so the server can still boot.

def _import_redis():
    import redis
    return redis

def _import_bot_detector():
    try:
        from ..filters.bot_detector import is_bot
    except ImportError:
        from filters.bot_detector import is_bot
    return is_bot

def _import_extractor():
    try:
        from ..extractors.playwright_extractor import get_skeleton
    except ImportError:
        from extractors.playwright_extractor import get_skeleton
    return get_skeleton

def _import_mapper():
    try:
        from ..mappers.coordinate_mapper import map_click_to_section
    except ImportError:
        from mappers.coordinate_mapper import map_click_to_section
    return map_click_to_section


def _get_redis_client():
    redis = _import_redis()
    return redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', 6379)), db=0)


def _get_supabase_client():
    from supabase import create_client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY are required")
    return create_client(url, key)


def get_pending_events(supabase_client, limit: int = 5000) -> List[Dict]:
    try:
        resp = supabase_client.table('raw_events').select('*').is_('section_id', None).limit(limit).execute()
        return resp.data or []
    except Exception as e:
        logger.exception("Failed fetching pending events: %s", e)
        return []


def group_by_session(events: List[Dict]) -> Dict[str, List[Dict]]:
    sessions = {}
    for ev in events:
        sid = ev.get('session_id') or ev.get('session') or 'unknown'
        sessions.setdefault(sid, []).append(ev)
    return sessions


def batch_update_events(supabase_client, updates: List[Dict]):
    """Use upsert to batch update section_id for events. Each update dict must include 'id' and 'section_id'."""
    if not updates:
        return
    try:
        supabase_client.table('raw_events').upsert(updates).execute()
        logger.info("Batched update of %d events", len(updates))
    except Exception:
        logger.exception("Failed batch update, falling back to per-row updates")
        for u in updates:
            try:
                supabase_client.table('raw_events').update({'section_id': u.get('section_id')}).eq('id', u.get('id')).execute()
            except Exception:
                logger.exception("Failed update for %s", u.get('id'))


def process_pending_events():
    logger.info("Starting Phase 2 processing job")
    try:
        redis_client = _get_redis_client()
        supabase_client = _get_supabase_client()
    except Exception:
        logger.exception("Phase 2 processing skipped because dependencies are unavailable")
        return

    is_bot = _import_bot_detector()
    get_skeleton = _import_extractor()
    map_click_to_section = _import_mapper()

    events = get_pending_events(supabase_client)
    if not events:
        logger.info("No pending events found")
        return

    sessions = group_by_session(events)
    updates = []
    bots = 0
    humans = 0

    for session_id, clicks in sessions.items():
        try:
            # Build clicks for analysis: require x,y,t
            click_list = []
            for c in clicks:
                if c.get('x') is None or c.get('y') is None or c.get('t') is None:
                    continue
                click_list.append({'x': c.get('x'), 'y': c.get('y'), 't': c.get('t')})

            if is_bot(session_id, click_list):
                bots += 1
                # Mark session as bot in DB (soft mark)
                try:
                    supabase_client.table('sessions').update({'is_bot': True}).eq('session_id', session_id).execute()
                except Exception:
                    logger.debug("Could not mark session %s as bot", session_id)
                continue

            humans += 1
            domain = clicks[0].get('domain')
            skeleton = get_skeleton(domain, redis_client)
            if not skeleton:
                logger.warning("[MISSING_SKELETON] domain=%s session=%s", domain, session_id)
                continue

            for ev in clicks:
                section = map_click_to_section(
                    ev.get('x'),
                    ev.get('y'),
                    ev.get('viewport_w') or ev.get('width') or 1920,
                    ev.get('viewport_h') or ev.get('height') or 1080,
                    skeleton,
                )
                if section:
                    updates.append({'id': ev.get('id'), 'section_id': section})
        except Exception:
            logger.exception("Session processing failed for %s; continuing", session_id)
            continue

    # Batch update
    batch_update_events(supabase_client, updates)
    logger.info("Phase 2 job complete: humans=%d bots=%d updates=%d", humans, bots, len(updates))
