"""
Observability service for JustiBot.
In-process metrics store backed by Upstash Redis — persists pipeline
performance events across backend restarts.
"""

import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# ── Groq pricing (per 1M tokens) ─────────────────────────────────────────────

GROQ_PRICING = {
    "openai/gpt-oss-20b": {"input": 0.075, "output": 0.30},
    "openai/gpt-oss-120b": {"input": 0.15, "output": 0.60},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Rough cost estimate based on Groq pricing.

    If exact token counts aren't available, callers should approximate
    input_tokens ≈ len(prompt) // 4 and output_tokens ≈ len(answer) // 4
    (rough tokens-per-char heuristic).
    """
    clean_model = model.replace(" (fast-path)", "")
    pricing = GROQ_PRICING.get(clean_model, GROQ_PRICING["openai/gpt-oss-20b"])
    cost = (
        input_tokens / 1_000_000 * pricing["input"]
        + output_tokens / 1_000_000 * pricing["output"]
    )
    return round(cost, 6)


# ── ObservabilityService ──────────────────────────────────────────────────────


class ObservabilityService:
    """
    Records per-request pipeline performance events to an Upstash Redis
    list and computes aggregate statistics over the stored window.
    """

    def __init__(self, redis_service):
        self.redis = redis_service
        self.METRICS_KEY = "observability:events"
        self.MAX_EVENTS = 500  # keep last 500 requests

    # ── Write ─────────────────────────────────────────────────────────────

    async def record_event(self, event: dict, user_uid: str) -> None:
        """
        Append a pipeline event to the Redis list.

        event shape:
        {
            "timestamp": str (ISO),
            "query_category": str,
            "model_used": str,
            "cache_hit": bool,
            "cache_type": "exact" | "semantic" | None,
            "timings_ms": { stage -> float },
            "hallucination_confidence": str,
            "estimated_cost_usd": float,
        }

        Non-fatal — logs and continues on any failure.
        """
        try:
            payload = json.dumps(event)
            key = f"{self.METRICS_KEY}:{user_uid}"
            self.redis.client.lpush(key, payload)
            self.redis.client.ltrim(key, 0, self.MAX_EVENTS - 1)
        except Exception as exc:
            logger.error("[OBSERVABILITY] Failed to record event: %s", exc)

    # ── Read ──────────────────────────────────────────────────────────────

    async def get_recent_events(self, user_uid: str, limit: int = 100) -> list[dict]:
        """Fetch the most recent *limit* events from the Redis list."""
        try:
            key = f"{self.METRICS_KEY}:{user_uid}"
            raw_items = self.redis.client.lrange(key, 0, limit - 1)
            events = []
            for raw in raw_items:
                try:
                    events.append(json.loads(raw))
                except (json.JSONDecodeError, TypeError):
                    continue
            return events
        except Exception as exc:
            logger.error("[OBSERVABILITY] Failed to fetch recent events: %s", exc)
            return []

    # ── Aggregation ───────────────────────────────────────────────────────

    async def get_aggregated_stats(self, user_uid: str) -> dict:
        """
        Compute aggregate statistics over all stored events.

        Returns:
        {
            "total_requests": int,
            "cache_hit_ratio": float,
            "cache_breakdown": {"exact": int, "semantic": int, "miss": int},
            "avg_latency_ms": { stage -> float },
            "category_breakdown": { category -> int },
            "model_breakdown": { model -> int },
            "hallucination_breakdown": { "high": int, "medium": int, "low": int },
            "total_estimated_cost_usd": float,
            "avg_cost_per_request_usd": float,
        }
        """
        try:
            key = f"{self.METRICS_KEY}:{user_uid}"
            raw_items = self.redis.client.lrange(key, 0, self.MAX_EVENTS - 1)
        except Exception as exc:
            logger.error("[OBSERVABILITY] Failed to fetch events for aggregation: %s", exc)
            raw_items = []

        events: list[dict] = []
        for raw in raw_items:
            try:
                events.append(json.loads(raw))
            except (json.JSONDecodeError, TypeError):
                continue

        total = len(events)
        if total == 0:
            return {
                "total_requests": 0,
                "cache_hit_ratio": 0.0,
                "cache_breakdown": {"exact": 0, "semantic": 0, "miss": 0},
                "avg_latency_ms": {},
                "category_breakdown": {},
                "model_breakdown": {},
                "hallucination_breakdown": {"high": 0, "medium": 0, "low": 0},
                "total_estimated_cost_usd": 0.0,
                "avg_cost_per_request_usd": 0.0,
            }

        # Cache
        cache_hits = sum(1 for e in events if e.get("cache_hit"))
        cache_breakdown: dict[str, int] = {"exact": 0, "semantic": 0, "miss": 0}
        for e in events:
            if e.get("cache_hit"):
                ct = e.get("cache_type", "exact")
                cache_breakdown[ct] = cache_breakdown.get(ct, 0) + 1
            else:
                cache_breakdown["miss"] += 1

        # Latency averages
        latency_sums: dict[str, float] = defaultdict(float)
        latency_counts: dict[str, int] = defaultdict(int)
        for e in events:
            timings = e.get("timings_ms", {})
            for stage, ms in timings.items():
                if isinstance(ms, (int, float)):
                    latency_sums[stage] += ms
                    latency_counts[stage] += 1
        avg_latency = {
            stage: round(latency_sums[stage] / latency_counts[stage], 2)
            for stage in latency_sums
            if latency_counts[stage] > 0
        }

        # Category breakdown
        category_breakdown: dict[str, int] = defaultdict(int)
        for e in events:
            cat = e.get("query_category", "UNKNOWN")
            category_breakdown[cat] += 1

        # Model breakdown
        model_breakdown: dict[str, int] = defaultdict(int)
        for e in events:
            model = e.get("model_used", "n/a")
            model_breakdown[model] += 1

        # Hallucination breakdown
        hall_breakdown: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        for e in events:
            conf = e.get("hallucination_confidence", "").lower()
            if conf in hall_breakdown:
                hall_breakdown[conf] += 1

        # Cost
        total_cost = sum(e.get("estimated_cost_usd", 0.0) for e in events)

        return {
            "total_requests": total,
            "cache_hit_ratio": round(cache_hits / total, 4) if total else 0.0,
            "cache_breakdown": dict(cache_breakdown),
            "avg_latency_ms": avg_latency,
            "category_breakdown": dict(category_breakdown),
            "model_breakdown": dict(model_breakdown),
            "hallucination_breakdown": hall_breakdown,
            "total_estimated_cost_usd": round(total_cost, 6),
            "avg_cost_per_request_usd": round(total_cost / total, 6) if total else 0.0,
        }
