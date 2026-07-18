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
        
        for i, candidate in enumerate(result[:3]):
            print(f"[RERANK-DEBUG] #{i}: raw_score={candidate.get('rerank_score')}, "
                  f"normalized_score={candidate.get('score')}, "
                  f"text_preview={candidate.get('text', '')[:80]}")

        return result

    def is_retrieval_weak(
        self,
        reranked_results: list[dict],
        min_gap_ratio: float = 1.5,
    ) -> bool:
        """
        Weak if the top result isn't meaningfully better than the
        bottom of the reranked set. Uses relative score separation
        instead of an absolute threshold, since the cross-encoder
        (trained on MS MARCO, not legal text) produces uncalibrated
        absolute scores on this domain — but relative ranking signal
        remains meaningful.
        """
        if len(reranked_results) < 2:
            return True
            
        scores = [r.get("rerank_score", r.get("score", 0.0)) for r in reranked_results]
        top_score = scores[0]
        bottom_score = scores[-1]

        # If everything scores roughly the same, the reranker isn't
        # distinguishing relevant from irrelevant — that's weak signal
        spread = top_score - bottom_score
        avg_score = sum(scores) / len(scores)

        # Weak if there's very little separation between best and worst,
        # OR if the top score isn't meaningfully above the average
        if spread < 0.02:  # near-flat distribution = no real signal
            return True
        if avg_score > 0 and (top_score / max(avg_score, 1e-6)) < min_gap_ratio:
            return True

        return False
