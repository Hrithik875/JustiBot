"""
Firebase JWT authentication middleware for JustiBot.
Verifies Firebase ID tokens from the Authorization header.
"""

import json
import logging

import firebase_admin
import firebase_admin.auth
from fastapi import Header, HTTPException
from firebase_admin import credentials

from backend.config import settings

logger = logging.getLogger(__name__)

# ── Initialize Firebase Admin SDK once at module load ──────────────────────────
try:
    service_account_dict = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
    cred = credentials.Certificate(service_account_dict)
    firebase_admin.initialize_app(cred)
    logger.info("[AUTH] Firebase Admin SDK initialized for project: %s", settings.FIREBASE_PROJECT_ID)
except ValueError:
    # Already initialized (e.g., during hot-reload or test runs)
    logger.debug("[AUTH] Firebase app already initialized — skipping.")
except Exception as exc:
    logger.error("[AUTH] Firebase initialization failed: %s", exc)
    raise


# ── Dependency ─────────────────────────────────────────────────────────────────

async def verify_firebase_token(
    authorization: str = Header(None),
) -> dict:
    """
    FastAPI dependency that verifies a Firebase ID token.

    Expects the Authorization header in the format:
        Authorization: Bearer <firebase_id_token>

    Returns:
        Decoded token dict containing at minimum 'uid' and 'email'.

    Raises:
        HTTPException 401: If the header is missing, malformed, or the
                           token is invalid / expired.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header",
        )

    token = authorization.split(" ", 1)[1]

    try:
        decoded_token = firebase_admin.auth.verify_id_token(token)
    except Exception as exc:
        logger.warning("[AUTH] Token verification failed: %s", exc)
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        ) from exc

    return decoded_token
