"""
BAI Telemetry API - Phase 1
Receives click telemetry from sensor.js and stores in Supabase

API Endpoints:
- GET /health - Health check
- GET /docs - Auto-generated Swagger UI
- POST /api/ingest - Receive telemetry batch
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import os
from datetime import datetime, timezone
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
# FASTAPI INITIALIZATION
# ============================================================

app = FastAPI(
    title="BAI Telemetry API",
    description="Sensor data ingestion for Behavior-Adaptive Interface",
    version="0.1.0",
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
# SUPABASE CONNECTION
# ============================================================

from supabase import create_client, Client

# Get credentials from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Optional[Client] = None

# Initialize Supabase client
if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("Connected to Supabase: %s", SUPABASE_URL)
    except Exception:
        logger.exception("Failed to connect to Supabase")
else:
    logger.warning("Supabase credentials are missing; database-backed endpoints will report degraded status")

# ============================================================
# ROUTES
# ============================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns:
        dict: Status and timestamp
    
    Example:
        GET /health
        Response: {"status": "ok", "timestamp": "2024-05-08T10:30:00"}
    """
    return {
        "status": "ok" if supabase else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected" if supabase else "not_configured"
    }


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


# Include routers
try:
    from .routers import ingest as ingest_router
except ImportError:
    from routers import ingest as ingest_router
app.include_router(ingest_router.router)

# Admin router for warm-up and debug
try:
    from .routers import admin as admin_router
except Exception:
    from routers import admin as admin_router
app.include_router(admin_router.router)


# ============================================================
# STARTUP/SHUTDOWN
# ============================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("BAI Telemetry API starting...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
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
