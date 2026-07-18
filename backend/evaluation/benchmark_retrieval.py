"""
JustiBot — Retrieval Method Comparison Benchmark.

Runs the same 20 test cases from test_set.py through four retrieval
configurations and measures recall@5 (via context_recall_proxy) and
wall-clock latency for each.

Usage:
    python -m backend.evaluation.benchmark_retrieval
"""

import json
import time
import logging
from pathlib import Path

from backend.corpus.embedder import Embedder
from backend.services.qdrant_service import QdrantService
from backend.services.bm25_service import BM25Service
from backend.services.hybrid_search_service import HybridSearchService
from backend.services.reranker_service import RerankerService
from backend.evaluation.test_set import TEST_CASES
from backend.evaluation.metrics import context_recall_proxy

# Suppress noisy INFO logs from services during benchmarking
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s",
)

# Only test cases that actually exercise retrieval (skip UNSAFE / OUT_OF_DOMAIN)
RETRIEVAL_CATEGORIES = {"LEGAL_SIMPLE", "LEGAL_COMPLEX"}

OUTPUT_PATH = Path(__file__).parent / "retrieval_benchmark_results.json"


def _format_results_for_bm25(bm25_results: list[dict]) -> list[dict]:
    """
    Normalise BM25Service output into the same shape that
    context_recall_proxy expects: list of dicts with a "text" key.
    """
    return [
        {
            "text": r.get("text", ""),
            "category": r.get("metadata", {}).get("category", ""),
        }
        for r in bm25_results
    ]


def _format_results_for_dense(dense_results: list[dict]) -> list[dict]:
    """Dense results from QdrantService already have "text" and "category"."""
    return dense_results


def main() -> None:
    print("=" * 70)
    print("RETRIEVAL METHOD COMPARISON BENCHMARK")
    print("=" * 70)

    # ── Initialise services ──────────────────────────────────────────────
    print("\n[BENCH] Initialising services...")
    embedder = Embedder()
    qdrant = QdrantService()
    bm25 = BM25Service(qdrant)
    hybrid = HybridSearchService(qdrant, bm25)
    reranker = RerankerService()
    print("[BENCH] All services ready.\n")

    # Filter to retrieval-eligible test cases only
    retrieval_cases = [
        tc for tc in TEST_CASES
        if tc["category"] in RETRIEVAL_CATEGORIES
    ]
    n = len(retrieval_cases)
    print(f"[BENCH] Running {n} retrieval-eligible test cases "
          f"(skipping UNSAFE / OUT_OF_DOMAIN / GREETING)\n")

    # ── Accumulators per method ──────────────────────────────────────────
    methods = ["Dense only", "BM25 only", "Hybrid (RRF)", "Hybrid + Reranker"]
    recall_sums = {m: 0.0 for m in methods}
    latency_sums = {m: 0.0 for m in methods}
    per_case_results = []

    for i, tc in enumerate(retrieval_cases, 1):
        query = tc["query"]
        ground_truth = tc["ground_truth_answer"]
        print(f"[BENCH] ({i}/{n}) {tc['id']}: {query[:60]}...")

        # Pre-compute embedding once (shared across dense, hybrid, hybrid+rerank)
        query_embedding = embedder.embed_query(query)

        case_result = {"id": tc["id"], "query": query}

        # ── 1. Dense only ────────────────────────────────────────────────
        t0 = time.perf_counter()
        dense_results = qdrant.search(
            query_embedding=query_embedding, category_filter=None, limit=5
        )
        t1 = time.perf_counter()
        dense_latency_ms = (t1 - t0) * 1000
        dense_recall = context_recall_proxy(dense_results, ground_truth)
        recall_sums["Dense only"] += dense_recall
        latency_sums["Dense only"] += dense_latency_ms
        case_result["dense_only"] = {
            "recall": dense_recall, "latency_ms": round(dense_latency_ms, 1)
        }

        # ── 2. BM25 only ────────────────────────────────────────────────
        t0 = time.perf_counter()
        bm25_raw = bm25.search(query=query, limit=5)
        t1 = time.perf_counter()
        bm25_latency_ms = (t1 - t0) * 1000
        bm25_formatted = _format_results_for_bm25(bm25_raw)
        bm25_recall = context_recall_proxy(bm25_formatted, ground_truth)
        recall_sums["BM25 only"] += bm25_recall
        latency_sums["BM25 only"] += bm25_latency_ms
        case_result["bm25_only"] = {
            "recall": bm25_recall, "latency_ms": round(bm25_latency_ms, 1)
        }

        # ── 3. Hybrid (RRF, no rerank) ──────────────────────────────────
        t0 = time.perf_counter()
        hybrid_results = hybrid.search(
            query=query, query_embedding=query_embedding,
            category_filter=None, limit=5
        )
        t1 = time.perf_counter()
        hybrid_latency_ms = (t1 - t0) * 1000
        hybrid_recall = context_recall_proxy(hybrid_results, ground_truth)
        recall_sums["Hybrid (RRF)"] += hybrid_recall
        latency_sums["Hybrid (RRF)"] += hybrid_latency_ms
        case_result["hybrid"] = {
            "recall": hybrid_recall, "latency_ms": round(hybrid_latency_ms, 1)
        }

        # ── 4. Hybrid + Reranker ────────────────────────────────────────
        t0 = time.perf_counter()
        hybrid_candidates = hybrid.search(
            query=query, query_embedding=query_embedding,
            category_filter=None, limit=30
        )
        reranked = reranker.rerank(query=query, candidates=hybrid_candidates, top_k=5)
        t1 = time.perf_counter()
        reranked_latency_ms = (t1 - t0) * 1000
        reranked_recall = context_recall_proxy(reranked, ground_truth)
        recall_sums["Hybrid + Reranker"] += reranked_recall
        latency_sums["Hybrid + Reranker"] += reranked_latency_ms
        case_result["hybrid_reranker"] = {
            "recall": reranked_recall, "latency_ms": round(reranked_latency_ms, 1)
        }

        per_case_results.append(case_result)

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"RETRIEVAL METHOD COMPARISON (n={n} test cases)")
    print("-" * 70)
    print(f"{'Method':<25} {'Avg Recall@5':>14} {'Avg Latency (ms)':>18}")
    print("-" * 70)

    summary = {}
    for m in methods:
        avg_recall = round(recall_sums[m] / n, 3)
        avg_latency = round(latency_sums[m] / n, 1)
        print(f"{m:<25} {avg_recall:>14.3f} {avg_latency:>15.1f}ms")
        summary[m] = {
            "avg_recall_at_5": avg_recall,
            "avg_latency_ms": avg_latency,
        }

    print("=" * 70)
    print(f"\nRun with: python -m backend.evaluation.benchmark_retrieval")

    # ── Save to JSON ─────────────────────────────────────────────────────
    output = {
        "n_test_cases": n,
        "summary": summary,
        "per_case": per_case_results,
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"[BENCH] Results saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
