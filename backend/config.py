"""
Application configuration for JustiBot backend.
Loads all settings from environment variables / .env file.
"""

from pathlib import Path

from pydantic_settings import BaseSettings

# Always resolve .env relative to this file (backend/.env),
# regardless of which directory the process is started from.
_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    """
    Centralized configuration loaded from environment variables.
    All secrets must be provided via .env or the system environment.
    """

    # Qdrant Cloud
    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION: str = "justibot_legal"

    # Groq LLM
    GROQ_API_KEY: str

    # Upstash Redis (REST API)
    UPSTASH_REDIS_URL: str
    UPSTASH_REDIS_TOKEN: str

    # Firebase Auth
    FIREBASE_PROJECT_ID: str
    FIREBASE_SERVICE_ACCOUNT_JSON: str  # Full service account JSON as a string

    # Application settings
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    RATE_LIMIT_PER_MINUTE: int = 20
    CACHE_TTL_SECONDS: int = 86400  # 24 hours
    ENVIRONMENT: str = "development"

    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"


# Single shared settings instance used throughout the app
settings = Settings()
