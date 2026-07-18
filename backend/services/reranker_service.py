"""
Cross-encoder reranking service for JustiBot.

Uses the ms-marco-MiniLM-L-6-v2 cross-encoder to re-score the top-30
fused candidates and select the best 5 for context injection into the LLM.
"""

import math
from sentence_transformers import CrossEncoder


CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class RerankerService:
    """
    Reranks hybrid-fused candidates with a cross-encoder for precision.

    The cross-encoder jointly encodes (query, passage) pairs which gives
    a much better relevance signal than either BM25 scores or cosine
    similarity from separate encoders.

    The model is loaded once at startup and kept in memory.
    """

    def __init__(self) -> None:
        """Load the cross-encoder model from HuggingFace Hub (or local cache)."""
        print(f"[RERANKER] Loading cross-encoder: {CROSS_ENCODER_MODEL} …")
        self.model = CrossEncoder(CROSS_ENCODER_MODEL)
        print(f"[RERANKER] Cross-encoder loaded: {CROSS_ENCODER_MODEL}")

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Cross-encode each candidate against the query and return top-k.

        Args:
            query:      The user's query string.
            candidates: List of candidate dicts (from HybridSearchService).
                        Each must have a "text" field.
            top_k:      Number of top results to keep.

        Returns:
            Top-k candidates (sorted descending by rerank_score), each
            augmented with a "rerank_score" float field.
        """
        if not candidates:
            return []

        # Truncate text to 400 chars to dramatically speed up CPU inference.
        # The first 400 chars are usually sufficient for the cross-encoder to judge relevance.
        pairs = [(query, candidate["text"][:400]) for candidate in candidates]

        scores = self.model.predict(pairs)

        # Attach the cross-encoder score to each candidate (mutates copies)
        scored = []
        for i, candidate in enumerate(candidates):
            raw_score = float(scores[i])
            normalized_score = 1 / (1 + math.exp(-raw_score))
            entry = {**candidate, "rerank_score": normalized_score}
            scored.append(entry)

        # Sort descending by rerank score
        scored.sort(key=lambda x: x["rerank_score"], reverse=True)

        result = scored[:top_k]

        print(f"[RERANK] {len(candidates)} candidates -> top {top_k}")

        return result

    def is_retrieval_weak(
        self,
        reranked_results: list[dict],
        score_threshold: float = 0.15,
    ) -> bool:
        """
        Returns True if retrieval is weak — meaning the reranker itself
        is not confident any of the top results are relevant.

        A cross-encoder score near 0 (after sigmoid normalization already
        applied in rerank()) indicates the model doesn't think the chunk
        is relevant to the query.

        Weak if: the TOP result's normalized rerank score is below
        score_threshold, OR fewer than 2 results exist at all.
        """
        if len(reranked_results) < 2:
            return True
        top_score = reranked_results[0].get("score", 0.0)
        return top_score < score_threshold
