"""
JustiBot — Pipeline Latency Breakdown Report.

Reads existing observability data from Redis to generate a latency breakdown
table across all logged requests.
"""

import asyncio
import json
from pathlib import Path

from backend.services.redis_service import RedisService
from backend.services.observability_service import ObservabilityService

# Provide a fixed test user ID since we're generating stats for a single-user
# or local deployment scenario.
TEST_USER_ID = "default_user"
OUTPUT_PATH = Path(__file__).parent / "latency_report.json"

STAGE_ORDER = [
    "classification",
    "embedding",
    "hybrid_search",
    "reranking",
    "generation",
    "hallucination_check",
    "total"
]


async def main() -> None:
    print("=" * 70)
    print("PIPELINE LATENCY BREAKDOWN")
    print("=" * 70)

    # Initialize services
    redis_service = RedisService()
    obs_service = ObservabilityService(redis_service)

    # Note: In a real multi-user scenario, we might iterate over all users.
    # For this portfolio project, stats are likely logged under a default or single user.
    # We will try a few common keys if default_user is empty.
    stats = await obs_service.get_aggregated_stats(TEST_USER_ID)
    
    n_events = stats.get("total_requests", 0)
    
    # If no events, try fetching all keys from Redis to see if they are under a specific UID
    if n_events == 0:
        keys = redis_service.client.keys(f"{obs_service.METRICS_KEY}:*")
        if keys:
            uid = keys[0].split(":")[-1]
            print(f"[INFO] Using data from user {uid}")
            stats = await obs_service.get_aggregated_stats(uid)
            n_events = stats.get("total_requests", 0)

    if n_events == 0:
        print(f"Based on 0 events — run more queries through the app for a more representative sample.")
        return

    print(f"PIPELINE LATENCY BREAKDOWN (from {n_events} live observability events)")
    print("-" * 70)
    print(f"{'Stage':<25} {'Avg (ms)':>15} {'% of Total':>15}")
    print("-" * 70)

    avg_latency = stats.get("avg_latency_ms", {})
    
    # Calculate a rough total from the individual components if "total" isn't explicitly logged
    total_ms = avg_latency.get("total", 0.0)
    if total_ms == 0.0:
        total_ms = sum(ms for stage, ms in avg_latency.items() if stage != "total")
        
    report_data = []

    for stage in STAGE_ORDER:
        if stage == "total":
            ms = total_ms
        else:
            ms = avg_latency.get(stage, 0.0)
            
        if ms > 0:
            pct = (ms / total_ms) * 100 if total_ms > 0 else 0.0
            print(f"{stage.title().replace('_', ' '):<25} {ms:>13.1f}ms {pct:>14.1f}%")
            report_data.append({
                "stage": stage,
                "avg_ms": round(ms, 1),
                "pct_total": round(pct, 1)
            })
            
    # Add any stages not in STAGE_ORDER
    for stage, ms in avg_latency.items():
        if stage not in STAGE_ORDER and stage != "total":
            pct = (ms / total_ms) * 100 if total_ms > 0 else 0.0
            print(f"{stage.title().replace('_', ' '):<25} {ms:>13.1f}ms {pct:>14.1f}%")
            report_data.append({
                "stage": stage,
                "avg_ms": round(ms, 1),
                "pct_total": round(pct, 1)
            })

    print("=" * 70)
    if n_events < 20:
        print(f"Based on {n_events} events — run more queries through the app for a more representative sample.")
    print(f"Run with: python -m backend.evaluation.generate_latency_report")

    # Save to JSON
    output = {
        "n_events": n_events,
        "total_avg_latency_ms": round(total_ms, 1),
        "breakdown": report_data
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"[REPORT] Results saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
