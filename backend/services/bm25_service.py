"""
BM25 sparse retrieval service for JustiBot.

Builds a BM25Okapi index over the full Qdrant corpus at startup,
then provides fast keyword-based retrieval to complement dense search.
"""

import re
import string

import numpy as np
from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> list[str]:
    """
    Normalise and tokenise text for BM25 indexing / querying.

    Strategy: lowercase → strip punctuation → split on whitespace.
    Intentionally simple — no stopword removal — so BM25 can still
    score legal keyword matches (e.g. "section", "act", "rent").
    """
    text = text.lower()
    # Replace punctuation with spaces rather than stripping, so
    # "section-12" becomes ["section", "12"] rather than ["section12"]
    text = re.sub(r"[" + re.escape(string.punctuation) + r"]", " ", text)
    return [tok for tok in text.split() if tok]


class BM25Service:
    """
    Sparse retrieval via BM25Okapi over the full JustiBot legal corpus.

    Designed to be used alongside QdrantService (dense) and fused via
    HybridSearchService (RRF).  The index is built once at startup and
    held in memory; it does NOT update dynamically when new chunks are
    ingested (restart the service to refresh).
    """

    def __init__(self, qdrant_service) -> None:
        """
        Load every chunk from Qdrant, tokenise, and build the BM25 index.

        Args:
            qdrant_service: An initialised QdrantService instance with a
                            working `get_all_chunks()` method.
        """
        print("[BM25] Loading full corpus from Qdrant …")
        all_chunks = qdrant_service.get_all_chunks()

        self.corpus_texts: list[str] = []
        self.corpus_metadata: list[dict] = []
        tokenized_corpus: list[list[str]] = []

        for chunk in all_chunks:
            text = chunk.get("text", "")
            self.corpus_texts.append(text)
            self.corpus_metadata.append(chunk.get("metadata", {}))
            tokenized_corpus.append(_tokenize(text))

        self.bm25 = BM25Okapi(tokenized_corpus)

        n = len(self.corpus_texts)
        print(f"[BM25] Indexed {n} chunks")

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """
        Score the entire corpus against `query` and return the top results.

        Args:
            query: Raw natural-language query string.
            limit: Maximum number of results to return.

        Returns:
            List of result dicts, sorted descending by BM25 score:
            [
                {
                    "text":       str,
                    "metadata":   dict,   # source_url, chunk_index, category …
                    "bm25_score": float,
                }
            ]
        """
        tokenized_query = _tokenize(query)
        if not tokenized_query:
            return []

        scores: np.ndarray = self.bm25.get_scores(tokenized_query)

        # Pair each score with its corpus index, then take the top-limit
        top_indices = np.argsort(scores)[::-1][:limit]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            # BM25 scores of exactly 0.0 carry no signal — omit them
            # so they don't pollute RRF fusion with zero-weight entries.
            if score <= 0.0:
                continue
            results.append(
                {
                    "text": self.corpus_texts[idx],
                    "metadata": self.corpus_metadata[idx],
                    "bm25_score": score,
                }
            )

        return results
