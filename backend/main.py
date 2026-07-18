"""
JustiBot FastAPI application entry point.
Wires together CORS, rate limiting, routers, and middleware.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.middleware.rate_limit import limiter
from backend.routers.chat import router as chat_router
from backend.routers.health import router as health_router
from backend.routers.observability import router as observability_router

# ── App instance ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="JustiBot API",
    description="Indian Legal Assistant — RAG-powered chatbot",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

# ── Rate limiter state ─────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ───────────────────────────────────────────────────────────────────────

origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(observability_router, prefix="/api", tags=["observability"])

# ── Root ───────────────────────────────────────────────────────────────────────


@app.get("/")
async def root() -> dict:
    """Root endpoint — confirms the API is reachable."""
    return {"message": "JustiBot API", "docs": "/docs"}
