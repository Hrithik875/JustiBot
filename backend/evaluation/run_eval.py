"""
JustiBot Phase 4 — Offline Evaluation Runner.

Runs the complete RAG pipeline against the labeled test set and
produces a JSON report plus a printed summary.

Usage:
    python -m backend.evaluation.run_eval

What it does (per test case):
  1. Classify the query (QueryClassifierService).
  2. UNSAFE / OUT_OF_DOMAIN → record classification accuracy only,
     skip retrieval and generation.
  3. For all other categories:
       a. Embed query (Embedder)
       b. Hybrid search — dense + sparse RRF (HybridSearchService)
       c. Cross-encoder rerank — top-5 (RerankerService)
       d. Generate answer via Groq (GroqService.generate or generate_simple)
       e. Hallucination check (HallucinationCheckerService)
       f. Compute all 5 metrics (metrics module)
  4. Aggregate and print summary.
  5. Write full results to backend/evaluation/eval_results.json.

Nothing in this script modifies any existing service file — it only
imports and calls them, exactly as the live /chat endpoint does.
"""

import asyncio
import json
import logging
import time

from backend.corpus.embedder import Embedder
from backend.services.qdrant_service import QdrantService
from backend.services.bm25_service import BM25Service
from backend.services.hybrid_search_service import HybridSearchService
from backend.services.reranker_service import RerankerService
from backend.services.groq_service import GroqService
from backend.services.query_classifier_service import QueryClassifierService
from backend.services.hallucination_checker_service import HallucinationCheckerService
from backend.evaluation.test_set import TEST_CASES
from backend.evaluation import metrics

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,          # suppress INFO noise from services
    format="%(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("eval")

# Categories where we skip retrieval + generation entirely and only
# validate that the classifier correctly detected the intent.
SKIP_RETRIEVAL_CATEGORIES = {"UNSAFE", "OUT_OF_DOMAIN"}


async def run_evaluation() -> None:
    overall_start = time.time()

    # ── Initialise all pipeline services ──────────────────────────────────────
    print("[EVAL] Initialising pipeline services...")
    print("[EVAL]  -> Loading Embedder (sentence-transformers all-MiniLM-L6-v2)...")
    embedder = Embedder()

    print("[EVAL]  -> Connecting to Qdrant...")
    qdrant = QdrantService()

    print("[EVAL]  -> Building BM25 index from Qdrant corpus...")
    bm25 = BM25Service(qdrant)

    print("[EVAL]  -> Initialising HybridSearchService (RRF fusion)...")
    hybrid = HybridSearchService(qdrant, bm25)

    print("[EVAL]  -> Loading cross-encoder reranker...")
    reranker = RerankerService()

    print("[EVAL]  -> Initialising GroqService...")
    groq_svc = GroqService()

    print("[EVAL]  -> Initialising QueryClassifierService...")
    classifier = QueryClassifierService(groq_svc.client)

    print("[EVAL]  -> Initialising HallucinationCheckerService...")
    checker = HallucinationCheckerService()

    print(f"\n[EVAL] All services ready. Running {len(TEST_CASES)} test cases...\n")
    print("=" * 70)

    results: list[dict] = []

    for tc in TEST_CASES:
        tc_start = time.time()
        tc_id = tc["id"]
        query = tc["query"]
        print(f"\n[EVAL] ► {tc_id}: {query[:65]}...")

        try:
            # ── Step 1: Classify ───────────────────────────────────────────
            classification = await classifier.classify(query)
            actual_category = classification["category"]
            category_correct = actual_category == tc["category"]

            print(
                f"       Classification: expected={tc['category']} "
                f"got={actual_category} {'OK' if category_correct else 'FAIL'}"
            )

            # ── Step 2: Skip retrieval for UNSAFE / OUT_OF_DOMAIN ─────────
            if actual_category in SKIP_RETRIEVAL_CATEGORIES:
                elapsed = round(time.time() - tc_start, 2)
                results.append({
                    "id": tc_id,
                    "query": query,
                    "expected_category": tc["category"],
                    "actual_category": actual_category,
                    "category_correct": category_correct,
                    "latency_sec": elapsed,
                    "answer": None,
                    "model_used": None,
                    "metrics": {"classification_only": True},
                })
                print(f"       Skipped retrieval (safety gate). Latency: {elapsed}s")
                continue

            # ── Step 3a: Embed query ───────────────────────────────────────
            query_embedding = embedder.embed_query(query)

            # ── Step 3b: Hybrid search ─────────────────────────────────────
            fused = hybrid.search(
                query=query,
                query_embedding=query_embedding,
                limit=30,
            )

            # ── Step 3c: Rerank ────────────────────────────────────────────
            context_chunks = reranker.rerank(query, fused, top_k=5)

            # ── Step 3d: Generate ──────────────────────────────────────────
            if actual_category == "GREETING":
                gen_result = await groq_svc.generate_simple(query, [])
            elif actual_category == "LEGAL_SIMPLE":
                gen_result = await groq_svc.generate_simple(query, context_chunks)
            else:
                # LEGAL_COMPLEX, GENERAL, and any fallback
                gen_result = await groq_svc.generate(query, context_chunks, [])

            answer = gen_result["answer"]
            model_used = gen_result["model"]

            # ── Step 3e: Hallucination check ───────────────────────────────
            hallucination_check = checker.check(answer, context_chunks)

            # ── Step 3f: Compute metrics ───────────────────────────────────
            kw_coverage = metrics.keyword_coverage(
                answer, tc.get("must_contain_keywords", [])
            )
            ctx_precision = metrics.context_precision(
                context_chunks, tc.get("expected_topic", "")
            )
            ctx_recall = metrics.context_recall_proxy(
                context_chunks, tc.get("ground_truth_answer", "")
            )
            ans_relevance = metrics.answer_relevance(answer, query)
            faithfulness = metrics.faithfulness_from_checker(hallucination_check)

            elapsed = round(time.time() - tc_start, 2)

            results.append({
                "id": tc_id,
                "query": query,
                "expected_category": tc["category"],
                "actual_category": actual_category,
                "category_correct": category_correct,
                "latency_sec": elapsed,
                "answer": answer[:200] + ("..." if len(answer) > 200 else ""),
                "model_used": model_used,
                "metrics": {
                    "keyword_coverage": round(kw_coverage, 3),
                    "context_precision": round(ctx_precision, 3),
                    "context_recall": round(ctx_recall, 3),
                    "answer_relevance": round(ans_relevance, 3),
                    "faithfulness": round(faithfulness, 3),
                    "hallucination_confidence": hallucination_check["confidence"],
                },
            })

            print(
                f"       faithfulness={faithfulness:.2f} "
                f"kw_cov={kw_coverage:.2f} "
                f"ctx_pre={ctx_precision:.2f} "
                f"latency={elapsed}s"
            )

        except Exception as exc:
            elapsed = round(time.time() - tc_start, 2)
            logger.error("[EVAL] %s FAILED: %s", tc_id, exc, exc_info=True)
            results.append({
                "id": tc_id,
                "query": query,
                "expected_category": tc["category"],
                "actual_category": "ERROR",
                "category_correct": False,
                "latency_sec": elapsed,
                "answer": None,
                "model_used": None,
                "metrics": {"error": str(exc)},
            })
            print(f"       ERROR: {exc}")

    # -- Aggregate summary ------------------------------------------------------
    total_elapsed = round(time.time() - overall_start, 1)

    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)

    # Classification accuracy (all 20 cases)
    category_correct_count = sum(1 for r in results if r["category_correct"])
    total = len(results)
    pct = category_correct_count / total * 100 if total else 0
    print(f"Classification Accuracy : {category_correct_count}/{total} ({pct:.1f}%)")

    # Full-pipeline metrics (exclude UNSAFE/OUT_OF_DOMAIN and ERROR cases)
    scored_results = [
        r for r in results
        if isinstance(r["metrics"], dict)
        and "classification_only" not in r["metrics"]
        and "error" not in r["metrics"]
    ]

    if scored_results:
        n = len(scored_results)

        avg_kw        = sum(r["metrics"]["keyword_coverage"]   for r in scored_results) / n
        avg_precision = sum(r["metrics"]["context_precision"]  for r in scored_results) / n
        avg_recall    = sum(r["metrics"]["context_recall"]     for r in scored_results) / n
        avg_relevance = sum(r["metrics"]["answer_relevance"]   for r in scored_results) / n
        avg_faith     = sum(r["metrics"]["faithfulness"]       for r in scored_results) / n
        avg_latency   = sum(r["latency_sec"] for r in results) / total

        print(f"\nMetrics across {n} fully scored test cases:")
        print(f"  Avg Keyword Coverage   : {avg_kw:.3f}")
        print(f"  Avg Context Precision  : {avg_precision:.3f}")
        print(f"  Avg Context Recall     : {avg_recall:.3f}")
        print(f"  Avg Answer Relevance   : {avg_relevance:.3f}")
        print(f"  Avg Faithfulness       : {avg_faith:.3f}")
        print(f"\n  Avg Latency (all 20)  : {avg_latency:.2f}s")

        # -- Per-case breakdown table -----------------------------------
        print(f"\n{'ID':>8}  {'kw_cov':>6}  {'ctx_pre':>7}  {'ctx_rec':>7}  "
              f"{'ans_rel':>7}  {'faith':>5}  {'conf':>6}  {'cat_ok':>6}")
        print("-" * 68)
        for r in scored_results:
            m = r["metrics"]
            cat_ok = "OK" if r["category_correct"] else "FAIL"
            print(
                f"{r['id']:>8}  "
                f"{m['keyword_coverage']:>6.3f}  "
                f"{m['context_precision']:>7.3f}  "
                f"{m['context_recall']:>7.3f}  "
                f"{m['answer_relevance']:>7.3f}  "
                f"{m['faithfulness']:>5.2f}  "
                f"{m['hallucination_confidence']:>6}  "
                f"{cat_ok:>4}"
            )
    else:
        print("\nNo fully scored test cases (all were UNSAFE/OUT_OF_DOMAIN or errored).")

    print("=" * 70)
    print(f"\nTotal evaluation time: {total_elapsed}s")

    # ── Save full results ──────────────────────────────────────────────────────
    output_path = "backend/evaluation/eval_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"[EVAL] Full results saved → {output_path}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
