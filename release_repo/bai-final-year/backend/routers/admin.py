from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

try:
    from ..jobs.warm_skeletons import warm_domains_in_background
except ImportError:
    from jobs.warm_skeletons import warm_domains_in_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class WarmRequest(BaseModel):
    domains: List[str]
    concurrency: Optional[int] = 2
    retries: Optional[int] = 2


@router.post("/warm-skeletons")
def warm_skeletons(req: WarmRequest, background_tasks: BackgroundTasks):
    if not req.domains:
        raise HTTPException(status_code=400, detail="domains list is required")
    concurrency = max(1, min(req.concurrency or 2, 8))
    retries = max(0, min(req.retries or 0, 5))

    # Start background thread to warm domains
    try:
        background_tasks.add_task(warm_domains_in_background, req.domains, concurrency, retries)
        logger.info("Accepted warm request for %d domains (concurrency=%d)", len(req.domains), concurrency)
        return {"status": "accepted", "domains": len(req.domains)}
    except Exception as e:
        logger.exception("Failed to schedule warm job: %s", e)
        raise HTTPException(status_code=500, detail="Failed to schedule warm job")
