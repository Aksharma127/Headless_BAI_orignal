from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import os
import logging

from supabase import create_client

try:
    from ..schemas import IngestPayload, IngestResponse
except ImportError:
    from schemas import IngestPayload, IngestResponse

logger = logging.getLogger(__name__)

router = APIRouter()


MIN_DESKTOP_VIEWPORT_WIDTH = int(os.getenv("MIN_DESKTOP_VIEWPORT_WIDTH", "1024"))


def write_to_db(payload: dict):
    """Background task: write session + raw events to Supabase."""
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

    if not SUPABASE_URL or not (SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY):
        logger.error("Supabase credentials missing in background task")
        return

    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY)

        session_id = payload.get("session_id")
        domain = payload.get("domain")
        viewport = payload.get("viewport", {})
        interactions = payload.get("interactions", [])

        # Upsert session
        try:
            sb.table("sessions").upsert({
                "session_id": session_id,
                "last_active": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to upsert session {session_id}: {e}")

        try:
            viewport_w = int(viewport.get("width") or viewport.get("w"))
            viewport_h = int(viewport.get("height") or viewport.get("h"))
            if viewport_w <= 0 or viewport_h <= 0:
                raise ValueError("viewport dimensions must be positive")
        except Exception:
            logger.warning("Dropping telemetry with invalid viewport for session %s: %s", session_id, viewport)
            return

        rows = []
        malformed_events = 0
        dropped_events = 0

        for inter in interactions:
            t_raw = inter.get("t")
            x_raw = inter.get("x")
            y_raw = inter.get("y")

            if t_raw is None or x_raw is None or y_raw is None:
                malformed_events += 1
                continue

            try:
                t_ms = int(t_raw)
                x = int(x_raw)
                y = int(y_raw)
                if t_ms <= 0:
                    malformed_events += 1
                    continue
                event_time = datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc)
                rows.append({
                    "session_id": session_id,
                    "domain": domain,
                    "x": x,
                    "y": y,
                    "t": t_ms,
                    "section_id": None,
                    "ema_weight": 1.0,
                    "viewport_w": viewport_w,
                    "viewport_h": viewport_h,
                    "created_at": event_time.isoformat()
                })
            except Exception:
                malformed_events += 1

        inserted_events = 0
        if rows:
            try:
                sb.table("raw_events").insert(rows).execute()
                inserted_events = len(rows)
            except Exception as e:
                logger.error(
                    "Failed bulk insert for session %s (rows=%d): %s",
                    session_id,
                    len(rows),
                    e,
                )
                dropped_events += len(rows)

        logger.info(
            "Background write complete: session=%s total=%d inserted=%d malformed=%d dropped=%d",
            session_id,
            len(interactions),
            inserted_events,
            malformed_events,
            dropped_events,
        )

    except Exception:
        logger.exception("Background DB task failed")


@router.post("/api/ingest")
@router.post("/api/sync")
async def ingest(payload: IngestPayload, background_tasks: BackgroundTasks):
    """Receive telemetry, validate, schedule DB write, and return immediately."""

    try:
        # Drop small viewports (mobile) silently
        vp = payload.viewport
        width = None
        try:
            # payload.viewport may be a dict with 'width' or the old object with 'w'
            if isinstance(vp, dict):
                width_value = vp.get('width') or vp.get('w')
                width = int(width_value) if width_value is not None else None
            else:
                width = int(getattr(vp, 'w', None))
        except Exception:
            width = None

        if width is not None and width < MIN_DESKTOP_VIEWPORT_WIDTH:
            logger.info(f"Dropping mobile viewport ({width}px) for session {payload.session_id}")
            return JSONResponse(content={"status": "ignored", "reason": "mobile_viewport"})

        # Prepare raw payload dict and clear sensitive large objects early
        raw = payload.model_dump()

        # Schedule background DB write
        background_tasks.add_task(write_to_db, raw)

        # Immediately return success to client
        return IngestResponse(status="success", received=len(payload.interactions))

    except Exception as e:
        logger.error(f"Ingest handler error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
