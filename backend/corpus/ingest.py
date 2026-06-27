"""
JustiBot one-time corpus ingestion script.

Downloads Indian legal PDFs and HTML pages, chunks them, generates
embeddings with sentence-transformers, and uploads to Qdrant Cloud.
For sources whose PDFs are blocked by government servers, falls back
to curated hardcoded chunks from fallback_chunks.py.

Run from the project root:
    python -m backend.corpus.ingest           # add to existing collection
    python -m backend.corpus.ingest --fresh   # drop + recreate collection first

Prerequisites:
  - .env file with QDRANT_URL and QDRANT_API_KEY set
  - Packages from requirements.txt installed
"""

import os
import sys
import tempfile
import warnings

import requests
import urllib3

# Allow running as a module from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.corpus.chunker import DocumentChunker
from backend.corpus.embedder import Embedder
from backend.corpus.fallback_chunks import CPA_2019_CHUNKS
from backend.corpus.sources import LEGAL_HELPLINES, LEGAL_SOURCES
from backend.services.qdrant_service import QdrantService

# Sources that must use fallback chunks (PDF permanently blocked)
_FALLBACK_SHORT_NAMES = {"cpa_2019", "it_act_2000"}

# Fallback chunks keyed by short_name for quick lookup
_FALLBACK_MAP: dict[str, list[dict]] = {}
for _chunk in CPA_2019_CHUNKS:
    _key = _chunk["metadata"]["short_name"]
    _FALLBACK_MAP.setdefault(_key, []).append(_chunk)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def _download_pdf(url: str, dest_path: str) -> bool:
    """
    Stream-download a PDF to dest_path.
    Tries SSL verify=True first; retries with verify=False for sites
    with self-signed / untrusted certificates.
    Returns True on success, False on any error.
    """
    for verify_ssl in (True, False):
        try:
            if not verify_ssl:
                warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)
                print(f"[WARN] Retrying {url} with SSL verification disabled")
            with requests.get(
                url,
                stream=True,
                timeout=60,
                headers=_HEADERS,
                verify=verify_ssl,
            ) as response:
                response.raise_for_status()
                with open(dest_path, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=8192):
                        fh.write(chunk)
            return True
        except requests.exceptions.SSLError:
            continue  # retry without SSL verification
        except Exception as exc:
            print(f"[ERROR] Download failed for {url}: {exc}")
            return False
    print(f"[ERROR] Download failed after SSL fallback for {url}")
    return False


def _is_valid_pdf(path: str) -> bool:
    """Check that the downloaded file starts with the PDF magic bytes '%PDF'."""
    try:
        with open(path, "rb") as fh:
            return fh.read(4) == b"%PDF"
    except Exception:
        return False


def main(fresh: bool = False) -> None:
    # ── STEP 1 — Initialize ───────────────────────────────────────────────────
    print("[INGEST] Starting JustiBot corpus ingestion")
    print(f"[INGEST] Processing {len(LEGAL_SOURCES)} legal sources")
    if fresh:
        print("[INGEST] --fresh: will recreate collection from scratch")

    qdrant_service = QdrantService()
    chunker = DocumentChunker(chunk_size=800, chunk_overlap=150)
    embedder = Embedder()

    # ── STEP 2 — Ensure Qdrant collection exists ──────────────────────────────
    if fresh:
        qdrant_service.recreate_collection()
    else:
        qdrant_service.create_collection()

    total_vectors = 0

    # ── STEP 3 — Process each legal source ───────────────────────────────────
    for source in LEGAL_SOURCES:
        metadata = {
            "name": source["name"],
            "short_name": source["short_name"],
            "category": source["category"],
            "year": source["year"],
            "source_url": source["url"],
        }

        chunks: list[dict] = []

        # Sources permanently blocked by government servers → use fallback
        if source["short_name"] in _FALLBACK_SHORT_NAMES:
            chunks = _FALLBACK_MAP.get(source["short_name"], [])
            if chunks:
                print(f"[FALLBACK] {source['name']}: using {len(chunks)} hardcoded chunks")
            else:
                print(f"[WARN] No fallback chunks defined for {source['name']} — skipping.")
                continue

        elif source["source_type"] == "pdf":
            print(f"[DOWNLOAD] {source['name']}...")
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                if not _download_pdf(source["url"], tmp_path):
                    continue
                if not _is_valid_pdf(tmp_path):
                    print(f"[ERROR] Not a valid PDF for {source['name']} — skipping.")
                    continue
                chunks = chunker.chunk_pdf(tmp_path, metadata)
            except Exception as exc:
                print(f"[ERROR] Failed to process PDF {source['name']}: {exc}")
                continue
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        elif source["source_type"] == "html":
            try:
                chunks = chunker.chunk_html(source["url"], metadata)
            except Exception as exc:
                print(f"[ERROR] HTML fetch failed for {source['name']}: {exc}")
                continue

        if not chunks:
            print(f"[WARN] No chunks produced for {source['name']} — skipping upload.")
            continue

        texts = [chunk["text"] for chunk in chunks]
        embeddings = embedder.embed_batch(texts)
        qdrant_service.upsert_chunks(chunks, embeddings)
        total_vectors += len(chunks)
        print(f"[UPLOAD] {source['name']}: {len(chunks)} vectors uploaded")

    # ── STEP 4 — Upload helpline data ─────────────────────────────────────────
    helpline_chunks: list[dict] = []
    for h in LEGAL_HELPLINES:
        text = f"{h['name']}: Call {h['number']}"
        if h["url"]:
            text += f" or visit {h['url']}"
        helpline_chunks.append(
            {
                "text": text,
                "metadata": {
                    "name": h["name"],
                    "short_name": "helpline",
                    "category": "helpline",
                    "year": 2024,
                    "source_url": h["url"] or "",
                },
            }
        )

    helpline_embeddings = embedder.embed_batch([c["text"] for c in helpline_chunks])
    qdrant_service.upsert_chunks(helpline_chunks, helpline_embeddings)
    total_vectors += len(helpline_chunks)
    print(f"[UPLOAD] Helplines: {len(helpline_chunks)} entries uploaded")

    # ── STEP 5 — Summary ──────────────────────────────────────────────────────
    print("[INGEST] DONE - Complete")
    print(f"[INGEST] Total vectors uploaded: {total_vectors}")
    print(f"[INGEST] Collection: {qdrant_service.collection_name} on Qdrant Cloud")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="JustiBot corpus ingestion")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Drop and recreate the Qdrant collection before ingesting",
    )
    args = parser.parse_args()
    main(fresh=args.fresh)
