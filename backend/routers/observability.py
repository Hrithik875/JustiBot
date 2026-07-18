"""
Observability API endpoints for JustiBot.
Exposes aggregated pipeline performance stats and recent event history.
"""

from fastapi import APIRouter, Depends

from backend.middleware.auth import verify_firebase_token
from backend.services.observability_service import ObservabilityService
from backend.services.redis_service import RedisService

router = APIRouter()

# ── Service singletons ────────────────────────────────────────────────────────
redis = RedisService()
observability_svc = ObservabilityService(redis)


@router.get("/observability/stats")
async def get_stats(token: dict = Depends(verify_firebase_token)):
    """Returns aggregated pipeline performance stats."""
    stats = await observability_svc.get_aggregated_stats()
    return stats


@router.get("/observability/recent")
async def get_recent(
    limit: int = 50,
    token: dict = Depends(verify_firebase_token),
):
    """Returns the N most recent pipeline events for a timeline view."""
    events = await observability_svc.get_recent_events(limit)
    return {"events": events, "count": len(events)}
