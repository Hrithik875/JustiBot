"""
Per-user rate limiting middleware for JustiBot.
Uses slowapi backed by in-memory or Redis storage.
"""

from fastapi import Request
from slowapi import Limiter

from backend.config import settings


def _get_user_key(request: Request) -> str:
    """
    Extract the Firebase UID from request state if available,
    otherwise fall back to the client IP address.
    This ensures authenticated users share their own rate limit bucket.
    """
    return getattr(request.state, "user_uid", None) or request.client.host


# Shared Limiter instance — attach to FastAPI app in main.py
limiter = Limiter(key_func=_get_user_key)


async def get_rate_limit_key(request: Request) -> str:
    """
    FastAPI dependency that returns the rate limit key for the current request.
    Returns the user's Firebase UID if authenticated, else their IP.
    """
    return _get_user_key(request)
