"""
Upstash Redis caching service for JustiBot.
Provides query-level response caching with TTL to reduce Groq API calls.
"""

import hashlib
import json
import logging

from upstash_redis import Redis

from backend.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """
    Wrapper around Upstash Redis for caching LLM responses.
    All cache failures are non-fatal — the app continues without cache.
    """

    def __init__(self):
        self.client = Redis(
            url=settings.UPSTASH_REDIS_URL,
            token=settings.UPSTASH_REDIS_TOKEN,
        )
        self.ttl = settings.CACHE_TTL_SECONDS

    async def get_cached(self, key: str) -> dict | None:
        """
        Retrieve a cached response by key.

        Args:
            key: Cache key (typically a SHA256 hash of the query).

        Returns:
            Parsed dict if cache hit, None otherwise.
        """
        try:
            raw = self.client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("[REDIS] Cache get failed for key=%s: %s", key, exc)
            return None

    async def set_cached(self, key: str, value: dict) -> None:
        """
        Store a response in cache with the configured TTL.

        Args:
            key: Cache key.
            value: Dict to JSON-serialize and store.
        """
        try:
            self.client.set(key, json.dumps(value), ex=self.ttl)
        except Exception as exc:
            logger.warning("[REDIS] Cache set failed for key=%s: %s", key, exc)

    def make_cache_key(self, query: str) -> str:
        """
        Deterministic cache key from query text.
        Normalizes whitespace and casing so semantically identical
        queries share the same cache entry.

        Args:
            query: Raw user query string.

        Returns:
            SHA256 hex digest string.
        """
        normalized = query.strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
