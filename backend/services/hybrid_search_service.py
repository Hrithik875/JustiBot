"""
Hybrid search service for JustiBot.

Fuses dense vector search (Qdrant) and sparse BM25 retrieval using
Reciprocal Rank Fusion (RRF), producing a single ranked list that
benefits from both exact keyword matching and semantic similarity.
"""

from collections import defaultdict


RRF_K = 60  # Standard RRF constant — dampens the influence of very high-ranked docs


def _doc_key(metadata: dict) -> str:
    """
    Stable identifier for deduplication across dense and sparse result lists.

    Uses `source_url + chunk_index` because both retrieval paths store
    these fields in the metadata payload.
    """
    source_url = metadata.get("source_url", "")
    chunk_index = metadata.get("chunk_index", 0)
    return f"{source_url}::{chunk_index}"


class HybridSearchService:
    """
    Combines QdrantService (dense) and BM25Service (sparse) via RRF fusion.

    Fetch-more strategy: both retrievers fetch `limit * 6` (min 30) candidates
    so the fusion pool is deep enough for RRF to be meaningful before
    the cross-encoder reranker makes its final selection.
    """

    def __init__(self, qdrant_service, bm25_service) -> None:
        """
        Args:
            qdrant_service: Initialised QdrantService instance.
            bm25_service:   Initialised BM25Service instance.
        """
        self.qdrant = qdrant_service
        self.bm25 = bm25_service

    def search(
        self,
        query: str,
        query_embedding: list[float],
        category_filter: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Run dense + sparse retrieval and fuse results with RRF.

        RRF formula:  score(d) = Σ  1 / (k + rank_i(d))
                      over every ranked list in which d appears.

        Args:
            query:            Raw query text (used by BM25).
            query_embedding:  Query vector (used by Qdrant dense search).
            category_filter:  Optional Qdrant payload filter by category.
            limit:            Number of fused results to return.

        Returns:
            List of result dicts (sorted descending by rrf_score):
            [
                {
                    "text":        str,
                    "source_name": str,
                    "source_url":  str,
                    "category":    str,
                    "score":       float,   # kept for upstream compat (= rrf_score)
                    "chunk_index": int,
                    "dense_rank":  int | None,
                    "sparse_rank": int | None,
                    "rrf_score":   float,
                }
            ]
        """
        fetch_n = max(30, limit * 6)

        # ── Dense retrieval ──────────────────────────────────────────────────
        dense_results = self.qdrant.search(
            query_embedding=query_embedding,
            category_filter=category_filter,
            limit=fetch_n,
        )

        # ── Sparse retrieval ─────────────────────────────────────────────────
        sparse_results = self.bm25.search(query=query, limit=fetch_n)

        # ── Build a unified doc store (key → canonical dict) ─────────────────
        # We populate it from both result lists; dense wins for shared fields
        # because its metadata is richer (source_name, score, etc.).
        doc_store: dict[str, dict] = {}

        for rank, doc in enumerate(dense_results, start=1):
            key = f"{doc.get('source_url', '')}::{doc.get('chunk_index', 0)}"
            doc_store[key] = {
                "text":        doc.get("text", ""),
                "source_name": doc.get("source_name", ""),
                "source_url":  doc.get("source_url", ""),
                "category":    doc.get("category", ""),
                "chunk_index": doc.get("chunk_index", 0),
                "dense_score": doc.get("score", 0.0),
                "dense_rank":  rank,
                "sparse_rank": None,
            }

        for rank, doc in enumerate(sparse_results, start=1):
            meta = doc.get("metadata", {})
            key = _doc_key(meta)
            if key in doc_store:
                doc_store[key]["sparse_rank"] = rank
            else:
                doc_store[key] = {
                    "text":        doc.get("text", ""),
                    "source_name": meta.get("name", ""),
                    "source_url":  meta.get("source_url", ""),
                    "category":    meta.get("category", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "dense_score": 0.0,
                    "dense_rank":  None,
                    "sparse_rank": rank,
                }

        # ── Compute RRF scores ────────────────────────────────────────────────
        rrf_scores: dict[str, float] = defaultdict(float)

        for key, doc in doc_store.items():
            if doc["dense_rank"] is not None:
                rrf_scores[key] += 1.0 / (RRF_K + doc["dense_rank"])
            if doc["sparse_rank"] is not None:
                rrf_scores[key] += 1.0 / (RRF_K + doc["sparse_rank"])

        # ── Sort and take top-limit ───────────────────────────────────────────
        sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)
        top_keys = sorted_keys[:limit]

        fused_results = []
        for key in top_keys:
            doc = doc_store[key]
            rrf = rrf_scores[key]
            fused_results.append(
                {
                    "text":        doc["text"],
                    "source_name": doc["source_name"],
                    "source_url":  doc["source_url"],
                    "category":    doc["category"],
                    "chunk_index": doc["chunk_index"],
                    "score":       rrf,          # alias for downstream compat
                    "dense_rank":  doc["dense_rank"],
                    "sparse_rank": doc["sparse_rank"],
                    "rrf_score":   rrf,
                }
            )

        print(
            f"[HYBRID] Dense: {len(dense_results)}, "
            f"Sparse: {len(sparse_results)}, "
            f"Fused: {len(fused_results)} (from {len(doc_store)} unique docs)"
        )

        return fused_results
