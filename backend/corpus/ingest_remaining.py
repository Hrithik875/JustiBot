"""
Uploads hardcoded key-provisions chunks for Consumer Protection Act 2019
and Information Technology Act 2000 directly to Qdrant.

Used because all government PDF hosts block programmatic downloads for these two acts.
The fallback_chunks.py file contains curated section summaries covering the most
commonly queried provisions.

Run from project root:
    python -m backend.corpus.ingest_remaining
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.corpus.embedder import Embedder
from backend.corpus.fallback_chunks import CPA_2019_CHUNKS
from backend.services.qdrant_service import QdrantService


def main():
    print("[INGEST] Uploading CPA 2019 + IT Act 2000 fallback chunks")

    qdrant = QdrantService()
    embedder = Embedder()

    all_chunks = CPA_2019_CHUNKS  # contains both CPA and IT Act chunks

    texts = [c["text"] for c in all_chunks]
    embeddings = embedder.embed_batch(texts)

    qdrant.upsert_chunks(all_chunks, embeddings)

    cpa_count = sum(1 for c in all_chunks if c["metadata"]["short_name"] == "cpa_2019")
    it_count = sum(1 for c in all_chunks if c["metadata"]["short_name"] == "it_act_2000")

    print(f"[UPLOAD] Consumer Protection Act 2019: {cpa_count} chunks uploaded")
    print(f"[UPLOAD] Information Technology Act 2000: {it_count} chunks uploaded")
    print(f"[INGEST] DONE - {len(all_chunks)} additional vectors uploaded")


if __name__ == "__main__":
    main()
