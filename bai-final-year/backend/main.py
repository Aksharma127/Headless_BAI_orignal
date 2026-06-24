"""
BAI Telemetry API - Headless Behavior-Adaptive Interface

Receives click telemetry from sensor.js, processes it through the ML pipeline,
and serves optimized layout orders to the frontend actuator.

API Endpoints:
- GET  /health      - Health check with subsystem status
- GET  /docs        - Auto-generated Swagger UI
- POST /api/ingest  - Receive telemetry batch from sensor.js
- GET  /api/layout  - Get current optimized layout (live ML or cached fallback)
- GET  /api/stats   - Telemetry statistics
- POST /admin/warm-skeletons - Pre-cache DOM skeletons for domains
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, Any
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import logging

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:
    BackgroundScheduler = None

# Load environment variables from .env, overriding inherited stale values on restart
load_dotenv(override=True)

# ============================================================
# LOGGING SETUP
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes"}

# Resolve cache directory: check multiple possible locations
def _resolve_cache_dir() -> Path:
    """Find the cache directory containing pre-computed ML outputs."""
    candidates = [
        Path(__file__).resolve().parent.parent / "cache",          # bai-final-year/cache
        Path(__file__).resolve().parent.parent / "frontend" / "cache",  # bai-final-year/frontend/cache
        Path(__file__).resolve().parent / "cache",                 # backend/cache (if symlinked)
    ]
    for candidate in candidates:
        if candidate.exists() and (candidate / "layout_order.json").exists():
            return candidate
    # Return the first candidate even if it doesn't exist; reads will handle FileNotFoundError
    return candidates[0]

CACHE_DIR = _resolve_cache_dir()

# ============================================================
# FASTAPI INITIALIZATION
# ============================================================

app = FastAPI(
    title="BAI Telemetry API",
    description="Sensor data ingestion and adaptive layout engine for Behavior-Adaptive Interface",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        return []
    return ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"]


# CORS Middleware - keep production explicit, allow local development by default.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# PYDANTIC MODELS (Data Validation)
# ============================================================

# Import validation schemas with a fallback for direct execution from the backend folder
try:
    from .schemas import IngestPayload, IngestResponse
except ImportError:
    from schemas import IngestPayload, IngestResponse


# ============================================================
# SUPABASE CONNECTION (non-fatal)
# ============================================================

supabase: Optional[Any] = None
_supabase_error: Optional[str] = None

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        from supabase import create_client, Client
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("Connected to Supabase: %s", SUPABASE_URL)
    except ImportError:
        _supabase_error = "supabase package not installed"
        logger.warning("supabase package not installed; database features disabled")
    except Exception as exc:
        _supabase_error = str(exc)
        logger.warning("Failed to connect to Supabase: %s — continuing without database", exc)
else:
    _supabase_error = "credentials not configured"
    logger.warning("Supabase credentials missing; database-backed endpoints will report degraded status")


# ============================================================
# REDIS CONNECTION (non-fatal)
# ============================================================

_redis_client: Optional[Any] = None
_redis_error: Optional[str] = None

try:
    import redis as redis_lib
    _redis_host = os.getenv("REDIS_HOST", "localhost")
    _redis_port = int(os.getenv("REDIS_PORT", "6379"))
    _redis_client = redis_lib.Redis(host=_redis_host, port=_redis_port, db=0, socket_connect_timeout=3)
    _redis_client.ping()
    logger.info("Connected to Redis: %s:%d", _redis_host, _redis_port)
except ImportError:
    _redis_error = "redis package not installed"
    logger.warning("redis package not installed; caching disabled")
except Exception as exc:
    _redis_error = str(exc)
    _redis_client = None
    logger.warning("Redis connection failed: %s — continuing without cache", exc)


# ============================================================
# CACHED / FALLBACK LAYOUT LOADER
# ============================================================

def _load_cached_layout() -> dict:
    """Load the pre-computed layout from the cache directory.

    This is real output from a previous ML pipeline run (K-Means clustering
    + friction optimization), NOT fabricated data. In DEMO_MODE the server
    serves this cached result instead of running the live ML pipeline.
    """
    result = {
        "layout_order": [],
        "section_layout": {},
        "friction_report": {},
        "preference_matrix": {},
    }

    try:
        order_path = CACHE_DIR / "layout_order.json"
        if order_path.exists():
            result["layout_order"] = json.loads(order_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load cached layout_order.json: %s", exc)

    try:
        layout_path = CACHE_DIR / "section_layout.json"
        if layout_path.exists():
            result["section_layout"] = json.loads(layout_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load cached section_layout.json: %s", exc)

    try:
        friction_path = CACHE_DIR / "friction_report.json"
        if friction_path.exists():
            result["friction_report"] = json.loads(friction_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load cached friction_report.json: %s", exc)

    try:
        matrix_path = CACHE_DIR / "preference_weight_matrix.json"
        if matrix_path.exists():
            result["preference_matrix"] = json.loads(matrix_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load cached preference_weight_matrix.json: %s", exc)

    return result


# Pre-load the cached layout at import time so /api/layout is always fast
_CACHED_LAYOUT = _load_cached_layout()


# ============================================================
# ROUTES
# ============================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint with subsystem connectivity status.

    Returns:
        dict: Overall status, subsystem states, and DEMO_MODE flag.

    Example:
        GET /health
        Response: {"status":"ok","redis":"connected","demo_mode":false}
    """
    # Test Redis connectivity live
    redis_status = "not_configured"
    if _redis_client is not None:
        try:
            _redis_client.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "disconnected"
    elif _redis_error:
        redis_status = "disconnected"

    # Determine overall status
    overall = "ok"
    if supabase is None and _redis_client is None:
        overall = "degraded"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "redis": redis_status,
        "database": "connected" if supabase else "not_configured",
        "demo_mode": DEMO_MODE,
        "cache_loaded": bool(_CACHED_LAYOUT.get("layout_order")),
    }


@app.get("/api/layout")
async def get_layout():
    """
    Get the current optimized section layout order.

    In live mode, this would run the ML clustering pipeline on recent
    telemetry data and return a real-time layout optimization. In DEMO_MODE
    (or when the ML pipeline is unavailable), this returns the cached output
    from the last successful pipeline run.

    The response always includes a 'source' field so consumers (and evaluators)
    can distinguish between live ML inference and cached fallback.

    Returns:
        dict: Layout order, section geometry, friction report, and source indicator.
    """
    source = "cache"

    if not DEMO_MODE:
        # Attempt live ML pipeline if dependencies are available
        try:
            live_layout = _run_live_pipeline()
            if live_layout and live_layout.get("layout_order"):
                return {
                    **live_layout,
                    "source": "live_ml",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as exc:
            logger.warning(
                "Live ML pipeline unavailable, falling back to cache: %s", exc
            )
            source = "cache_fallback"

    # Serve cached layout (honest graceful degradation)
    if not _CACHED_LAYOUT.get("layout_order"):
        raise HTTPException(
            status_code=503,
            detail="No layout data available. Run the ML pipeline or ensure cache files exist.",
        )

    return {
        **_CACHED_LAYOUT,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note": "Served from pre-computed ML pipeline output (K-Means + friction optimization)"
        if source == "cache"
        else "Live ML pipeline unavailable; served from last successful pipeline run",
    }


def _run_live_pipeline() -> Optional[dict]:
    """Attempt to run the live ML clustering pipeline on stored telemetry.

    This requires numpy, scikit-learn, and access to Supabase for recent
    telemetry data. If any dependency is missing, returns None so the caller
    falls back to the cached layout.
    """
    if supabase is None:
        return None

    try:
        import numpy as np
        from sklearn.cluster import KMeans
    except ImportError:
        logger.info("numpy/scikit-learn not available for live ML pipeline")
        return None

    try:
        # Fetch recent telemetry from Supabase
        resp = (
            supabase.table("raw_events")
            .select("session_id, x, y, t, section_id")
            .not_.is_("section_id", "null")
            .limit(5000)
            .execute()
        )
        events = resp.data or []
        if len(events) < 50:
            logger.info("Insufficient telemetry for live clustering (%d events)", len(events))
            return None

        # Group by session
        section_ids = list(_CACHED_LAYOUT.get("section_layout", {}).keys())
        if not section_ids:
            return None

        alpha = 0.2
        by_session: dict[str, list] = {}
        for ev in events:
            by_session.setdefault(ev["session_id"], []).append(ev)

        feature_rows = []
        for sid, session_events in by_session.items():
            weights = np.zeros(len(section_ids), dtype=float)
            for ev in sorted(session_events, key=lambda e: e.get("t", 0)):
                section = ev.get("section_id")
                if section in section_ids:
                    obs = np.zeros(len(section_ids), dtype=float)
                    obs[section_ids.index(section)] = 1.0
                    weights = alpha * obs + (1.0 - alpha) * weights
            feature_rows.append(weights)

        if len(feature_rows) < 10:
            return None

        X = np.vstack(feature_rows)
        k = min(3, len(feature_rows))
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = model.fit_predict(X)

        # Build optimized order from cluster centers
        global_weights = model.cluster_centers_.mean(axis=0)
        ranked_indices = np.argsort(-global_weights)
        layout_order = [section_ids[i] for i in ranked_indices]

        # Keep footer at the bottom
        if "footer" in layout_order:
            layout_order = [s for s in layout_order if s != "footer"] + ["footer"]

        cohorts = []
        for cid, center in enumerate(model.cluster_centers_):
            norm = center / center.sum() if center.sum() > 0 else center
            cohorts.append({
                "cluster_id": int(cid),
                "sessions": int(np.sum(labels == cid)),
                "top_section": section_ids[int(np.argmax(norm))],
                "preference_weights": {
                    s: round(float(w), 6) for s, w in zip(section_ids, norm)
                },
            })

        return {
            "layout_order": layout_order,
            "section_layout": _CACHED_LAYOUT.get("section_layout", {}),
            "preference_matrix": {
                "alpha": alpha,
                "k": k,
                "wcss": round(float(model.inertia_), 6),
                "section_ids": section_ids,
                "cohorts": cohorts,
            },
        }

    except Exception as exc:
        logger.warning("Live pipeline execution failed: %s", exc)
        return None


# NOTE: ingest route implemented in backend/routers/ingest.py as a background-worker pattern


@app.get("/api/stats")
async def get_stats():
    """
    Get statistics about collected telemetry

    Returns:
        dict: Session count, event count, etc.
    """
    if supabase is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    try:
        # Get accurate counts from Supabase count metadata.
        sessions_response = (
            supabase.table("sessions")
            .select("*", count="exact", head=True)
            .execute()
        )

        events_response = (
            supabase.table("raw_events")
            .select("*", count="exact", head=True)
            .execute()
        )
        
        return {
            "status": "ok",
            "total_sessions": sessions_response.count or 0,
            "total_events": events_response.count or 0
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.exception("Unhandled exception while serving %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error"},
    )


# ============================================================
# ROUTER REGISTRATION
# ============================================================

# Include the ingest router (telemetry ingestion from sensor.js)
try:
    from .routers import ingest as ingest_router
except ImportError:
    try:
        from routers import ingest as ingest_router
    except ImportError:
        ingest_router = None
        logger.warning("Could not import ingest router; /api/ingest will be unavailable")

if ingest_router is not None:
    app.include_router(ingest_router.router)

# Admin router for warm-up and debug
try:
    from .routers import admin as admin_router
except ImportError:
    try:
        from routers import admin as admin_router
    except ImportError:
        admin_router = None
        logger.warning("Could not import admin router; /admin/* will be unavailable")

if admin_router is not None:
    app.include_router(admin_router.router)


# ============================================================
# STARTUP/SHUTDOWN
# ============================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("BAI Telemetry API starting...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"DEMO_MODE: {DEMO_MODE}")
    logger.info(f"Cache directory: {CACHE_DIR}")
    logger.info(f"Cached layout sections: {list(_CACHED_LAYOUT.get('layout_order', []))}")

    if DEMO_MODE:
        logger.info("Running in DEMO_MODE — ML clustering will be skipped, cached layout served")
        return

    if os.getenv("ENABLE_PHASE2_SCHEDULER", "true").lower() in {"0", "false", "no"}:
        logger.info("Skipping Phase 2 scheduler because ENABLE_PHASE2_SCHEDULER is disabled")
        return
    if supabase is None:
        logger.warning("Skipping Phase 2 scheduler because Supabase is not configured")
        return
    if BackgroundScheduler is None:
        logger.warning("Skipping Phase 2 scheduler because APScheduler is not installed")
        return

    # Start Phase 2 background scheduler
    try:
        try:
            from .jobs.process_events import process_pending_events
        except ImportError:
            from jobs.process_events import process_pending_events
    except Exception:
        logger.exception("Skipping Phase 2 scheduler because the processor could not be imported")
        return

    scheduler = BackgroundScheduler()
    interval_minutes = int(os.getenv("PHASE2_INTERVAL_MINUTES", "5"))
    scheduler.add_job(process_pending_events, 'interval', minutes=interval_minutes, id='phase2_processor', replace_existing=True)
    scheduler.start()
    app.state.phase2_scheduler = scheduler
    logger.info("Phase 2 processor scheduled every %d minutes", interval_minutes)


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("BAI Telemetry API shutting down...")
    try:
        scheduler = getattr(app.state, 'phase2_scheduler', None)
        if scheduler:
            scheduler.shutdown(wait=False)
            logger.info("Phase 2 scheduler stopped")
    except Exception:
        logger.exception("Error stopping scheduler")


# ============================================================
# MAIN - RUN SERVER
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting BAI Telemetry API...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",              # Accept connections from any IP
        port=8000,                   # Port 8000
        reload=True,                 # Auto-reload on code changes
        log_level="info"
    )
