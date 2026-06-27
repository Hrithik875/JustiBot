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

    # ── Semantic cache ────────────────────────────────────────────────────────

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two equal-length vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x ** 2 for x in a) ** 0.5
        norm_b = sum(x ** 2 for x in b) ** 0.5
        return dot / (norm_a * norm_b + 1e-8)

    async def store_semantic_key(
        self,
        query: str,
        embedding: list[float],
        cache_key: str,
    ) -> None:
        """
        Persist a query embedding so future similar queries can match it.
        Stored under key: semantic:{sha256_of_query}
        """
        semantic_key = f"semantic:{self.make_cache_key(query)}"
        value = {
            "embedding": embedding,
            "cache_key": cache_key,
            "query": query,
        }
        await self.set_cached(semantic_key, value)

    async def find_semantic_match(
        self,
        query_embedding: list[float],
        similarity_threshold: float = 0.92,
    ) -> dict | None:
        """
        Scan stored semantic keys and return a cached response if a
        sufficiently similar query has been answered before.

        Returns the cached response dict, or None on a miss.
        Performance: O(n) over stored semantic keys — acceptable for
        a portfolio project with <10 K cached queries.
        """
        try:
            keys = self.client.keys("semantic:*")
            if not keys:
                return None

            best_score = -1.0
            best_cache_key = None

            for key in keys:
                try:
                    raw = self.client.get(key)
                    if not raw:
                        continue
                    stored = json.loads(raw)
                    score = self._cosine_sim(query_embedding, stored["embedding"])
                    if score >= similarity_threshold and score > best_score:
                        best_score = score
                        best_cache_key = stored["cache_key"]
                except Exception:
                    continue

            if best_cache_key:
                return await self.get_cached(best_cache_key)

            return None
        except Exception as exc:
            logger.warning("[REDIS] Semantic search failed: %s", exc)
            return None
