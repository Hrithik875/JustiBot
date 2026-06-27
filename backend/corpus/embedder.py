"""
Embedding generation for JustiBot corpus ingestion.
Uses sentence-transformers all-MiniLM-L6-v2 (384-dim, free, local).
"""

import math
from sentence_transformers import SentenceTransformer


class Embedder:
    """
    Wraps sentence-transformers to produce normalized 384-dim embeddings.
    Runs entirely locally — no API calls required.
    """

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384

    def __init__(self):
        """Load the embedding model once at initialization."""
        self.model = SentenceTransformer(self.MODEL_NAME)
        print(f"[EMBEDDER] Model loaded: all-MiniLM-L6-v2 ({self.EMBEDDING_DIM} dims)")

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        """Return the L2-normalized unit vector."""
        magnitude = math.sqrt(sum(x * x for x in vector))
        if magnitude == 0.0:
            return vector
        return [x / magnitude for x in vector]

    def embed(self, text: str) -> list[float]:
        """
        Generate a normalized embedding for a single text string.

        Args:
            text: Input text to embed.

        Returns:
            Normalized embedding as a plain Python list of floats.
        """
        raw = self.model.encode(text, normalize_embeddings=False)
        return self._normalize(raw.tolist())

    def embed_query(self, query: str) -> list[float]:
        """
        Embed a single search query with query-specific prefix.
        sentence-transformers performs better with prefixed queries.
        """
        prefixed = f"Represent this legal query for searching: {query}"
        return self.embed(prefixed)

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Generate normalized embeddings for a list of texts in batches.

        Args:
            texts: List of input strings.
            batch_size: Number of texts to embed per batch.

        Returns:
            List of normalized embeddings as plain Python lists of floats.
        """
        all_embeddings: list[list[float]] = []
        total_batches = math.ceil(len(texts) / batch_size)

        for i in range(total_batches):
            batch = texts[i * batch_size : (i + 1) * batch_size]
            print(f"[EMBED] Batch {i + 1}/{total_batches}")
            raw_batch = self.model.encode(batch, normalize_embeddings=False)
            for raw in raw_batch:
                all_embeddings.append(self._normalize(raw.tolist()))

        return all_embeddings
