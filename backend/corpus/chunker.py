"""
Document chunking logic for JustiBot corpus ingestion.
Splits legal documents into overlapping chunks suitable for RAG retrieval.
"""

import re
import requests
from bs4 import BeautifulSoup


class DocumentChunker:
    """
    Splits documents into overlapping, sentence-aware chunks
    for embedding and Qdrant upload.
    """

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 80):
        """
        Args:
            chunk_size: Target characters per chunk.
            chunk_overlap: Character overlap between consecutive chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, metadata: dict) -> list[dict]:
        """
        Split text into overlapping chunks with sentence-aware boundaries.

        Args:
            text: Raw document text.
            metadata: Metadata dict to attach to each chunk.

        Returns:
            List of chunk dicts with text and metadata.
        """
        chunks = []
        text_length = len(text)
        start = 0
        chunk_index = 0

        while start < text_length:
            end = start + self.chunk_size

            if end >= text_length:
                # Last chunk: take the rest
                chunk_text = text[start:]
            else:
                # Try to find a sentence boundary near `end`
                # Prefer ". " or "\n" within the last 20% of the chunk
                search_start = end - int(self.chunk_size * 0.2)
                search_start = max(search_start, start)

                # Look for ". " boundary
                boundary = -1
                for pattern in [". ", "\n"]:
                    idx = text.rfind(pattern, search_start, end)
                    if idx != -1 and idx > boundary:
                        boundary = idx

                if boundary != -1:
                    end = boundary + 1  # Include the period
                chunk_text = text[start:end]

            stripped = chunk_text.strip()
            if len(stripped) >= 100:
                chunk_metadata = {
                    **metadata,
                    "chunk_index": chunk_index,
                    "char_start": start,
                }
                chunks.append({"text": stripped, "metadata": chunk_metadata})
                chunk_index += 1

            # Move start forward by chunk_size minus overlap
            step = self.chunk_size - self.chunk_overlap
            start += step

        return chunks

    def chunk_pdf(self, pdf_path: str, metadata: dict) -> list[dict]:
        """
        Extract text from a PDF file and chunk it.

        Args:
            pdf_path: Path to the local PDF file.
            metadata: Metadata dict to attach to chunks.

        Returns:
            List of chunk dicts.
        """
        from pypdf import PdfReader

        reader = PdfReader(pdf_path)
        page_count = len(reader.pages)

        full_text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"

        chunk_metadata = {**metadata, "page_count": page_count}
        chunks = self.chunk_text(full_text, chunk_metadata)

        print(f"[CHUNK] {metadata['name']}: {len(chunks)} chunks from {page_count} pages")
        return chunks

    def chunk_html(self, url: str, metadata: dict) -> list[dict]:
        """
        Fetch an HTML page, extract clean text, and chunk it.

        Args:
            url: URL of the HTML page.
            metadata: Metadata dict to attach to chunks.

        Returns:
            List of chunk dicts.
        """
        response = requests.get(url, timeout=30, headers={"User-Agent": "JustiBot/1.0"})
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        raw_text = soup.get_text(separator="\n")

        # Collapse 3+ consecutive newlines to 2
        cleaned_text = re.sub(r"\n{3,}", "\n\n", raw_text)

        chunks = self.chunk_text(cleaned_text, metadata)
        print(f"[CHUNK] {metadata['name']}: {len(chunks)} chunks from HTML")
        return chunks
