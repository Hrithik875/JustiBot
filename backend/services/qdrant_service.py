"""
Qdrant vector database service for JustiBot.
Handles collection management, vector upsert, and semantic search.
"""

from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from backend.config import settings

EMBEDDING_DIM = 384
BATCH_SIZE = 100
RELEVANCE_THRESHOLD = 0.35


class QdrantService:
    """Wrapper around the Qdrant Cloud client for JustiBot operations."""

    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=60,
        )
        self.collection_name = settings.QDRANT_COLLECTION

    def create_collection(self) -> None:
        """
        Ensure the Qdrant collection exists, creating it if necessary.
        Uses cosine distance with 384-dim vectors (all-MiniLM-L6-v2).
        """
        existing = {c.name for c in self.client.get_collections().collections}

        if self.collection_name in existing:
            print(f"[QDRANT] Collection already exists: {self.collection_name}")
        else:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )
            print(f"[QDRANT] Collection created: {self.collection_name}")

        print(f"[QDRANT] Collection ready: {self.collection_name}")

    def recreate_collection(self) -> None:
        """
        Drop the Qdrant collection if it exists, and recreate it from scratch.
        """
        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection_name in existing:
            print(f"[QDRANT] Deleting existing collection: {self.collection_name}")
            self.client.delete_collection(collection_name=self.collection_name)
        
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        print(f"[QDRANT] Collection recreated: {self.collection_name}")

    def upsert_chunks(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """
        Upload chunk text + metadata alongside their embeddings to Qdrant.

        Args:
            chunks: List of chunk dicts with 'text' and 'metadata' keys.
            embeddings: Corresponding embeddings (same length as chunks).
        """
        points: list[PointStruct] = []
        for chunk, embedding in zip(chunks, embeddings):
            payload = {**chunk["metadata"], "text": chunk["text"]}
            points.append(
                PointStruct(
                    id=str(uuid4()),
                    vector=embedding,
                    payload=payload,
                )
            )

        # Upload in batches to avoid request size limits
        for i in range(0, len(points), BATCH_SIZE):
            batch = points[i : i + BATCH_SIZE]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
            )

    def search(
        self,
        query_embedding: list[float],
        category_filter: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """
        Perform semantic search against the legal corpus.

        Args:
            query_embedding: Normalized query vector.
            category_filter: Optional category to restrict search scope.
            limit: Maximum number of results to return.

        Returns:
            List of result dicts with text, source info, and relevance score.
            Only includes results with score >= RELEVANCE_THRESHOLD.
        """
        qdrant_filter = None
        if category_filter:
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="category",
                        match=MatchValue(value=category_filter),
                    )
                ]
            )

        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=qdrant_filter,
            limit=limit,
        )

        results = []
        for hit in hits:
            if hit.score < RELEVANCE_THRESHOLD:
                continue
            results.append(
                {
                    "text": hit.payload.get("text", ""),
                    "source_name": hit.payload.get("name", ""),
                    "source_url": hit.payload.get("source_url", ""),
                    "category": hit.payload.get("category", ""),
                    "score": hit.score,
                    "chunk_index": hit.payload.get("chunk_index", 0),
                }
            )

        return results
