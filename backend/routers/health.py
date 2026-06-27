"""
Health check endpoints for JustiBot API.
Provides basic liveness and authenticated detailed connectivity checks.
"""

from fastapi import APIRouter, Depends

from backend.config import settings
from backend.middleware.auth import verify_firebase_token
from backend.services.qdrant_service import QdrantService
from backend.services.redis_service import RedisService

router = APIRouter()

# Shared service instances for health checks
_qdrant = QdrantService()
_redis = RedisService()
from backend.services.groq_service import GroqService
_groq_svc = GroqService()


@router.get("/health")
async def health_check() -> dict:
    """
    Basic liveness check — no authentication required.
    Returns service metadata and environment name.
    """
    return {
        "status": "healthy",
        "service": "JustiBot API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/detailed")
async def detailed_health(
    token: dict = Depends(verify_firebase_token),
) -> dict:
    """
    Detailed connectivity check — requires a valid Firebase ID token.
    Probes Qdrant and Redis; confirms Groq API key is configured.
    """
    # Qdrant connectivity
    try:
        collections = _qdrant.client.get_collections()
        collection_names = [c.name for c in collections.collections]
        qdrant_status = f"connected — collections: {collection_names}"
    except Exception as e:
        qdrant_status = f"error: {str(e)}"

    # Redis connectivity
    try:
        await _redis.set_cached("__ping__", {"ping": "pong"})
        result = await _redis.get_cached("__ping__")
        redis_status = "connected" if result else "error: read after write failed"
    except Exception as e:
        redis_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "qdrant": qdrant_status,
        "redis": redis_status,
        "groq": f"configured — model: {_groq_svc.model_name}",
        "vectors_collection": settings.QDRANT_COLLECTION
    }
