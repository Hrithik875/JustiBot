"""
Lightweight hallucination checker for JustiBot.

Runs AFTER Groq generation, BEFORE the response is returned.
Performs two fast, local (zero-cost, zero-latency) checks:

  1. Citation Presence — extracts legal citations from the answer
     and verifies each one appears in the retrieved context chunks.
  2. Lexical Overlap   — computes a keyword-overlap ratio between
     the answer and the retrieved context as a rough proxy for
     groundedness.

No additional LLM calls are made here.  This is purely text
analysis and adds < 10 ms to the response time.
"""

import re
import string

# ---------------------------------------------------------------------------
# Stopwords — small hardcoded list sufficient for Indian legal text
# ---------------------------------------------------------------------------
_STOPWORDS = frozenset({
    "the", "and", "for", "are", "was", "this", "that", "with",
    "from", "not", "have", "has", "been", "they", "will", "its",
    "also", "such", "any", "may", "shall", "under", "upon",
    "their", "which", "where", "when", "who", "what", "how",
    "can", "all", "but", "your", "you", "she", "him", "her",
    "his", "our", "into", "more", "than", "then", "being",
    "there", "were", "said", "those", "these", "each", "both",
})

# ---------------------------------------------------------------------------
# Citation patterns
# ---------------------------------------------------------------------------
_SECTION_PATTERN   = re.compile(r'\bSection\s+\d+[A-Za-z]?\b', re.IGNORECASE)
_ARTICLE_PATTERN   = re.compile(r'\bArticle\s+\d+[A-Za-z]?\b', re.IGNORECASE)

# Named acts / abbreviations — ordered longest-first to avoid partial matches
_NAMED_ACTS = [
    "Bharatiya Nyaya Sanhita",
    "Bharatiya Nagarik Suraksha Sanhita",
    "Bharatiya Sakshya Adhiniyam",
    "Consumer Protection Act",
    "Constitution of India",
    "Right to Information Act",
    "RTI Act",
    "IT Act",
    "IPC",
    "BNS",
    "BNSS",
    "CrPC",
    "CPC",
]
_ACT_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(a) for a in _NAMED_ACTS) + r')\b',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class HallucinationCheckerService:
    """Pure text-analysis hallucination checker — no model loading required."""

    def __init__(self) -> None:
        pass  # intentionally lightweight

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> set[str]:
        """
        Lowercase, strip punctuation, split on whitespace, remove
        stopwords and very short words (≤ 3 chars).
        """
        translator = str.maketrans("", "", string.punctuation)
        words = text.lower().translate(translator).split()
        return {w for w in words if len(w) > 3 and w not in _STOPWORDS}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_citations(self, text: str) -> list[str]:
        """
        Extract legal citations from *text* using regex patterns:
          - "Section <n>"   e.g. "Section 302", "Section 66F"
          - "Article <n>"   e.g. "Article 21"
          - Named acts / abbreviations (IPC, BNS, RTI Act, …)

        Returns a deduplicated list preserving original casing of the
        first occurrence for readability.
        """
        found: dict[str, str] = {}  # normalised_key -> original match

        for m in _SECTION_PATTERN.finditer(text):
            key = m.group().lower()
            found.setdefault(key, m.group())

        for m in _ARTICLE_PATTERN.finditer(text):
            key = m.group().lower()
            found.setdefault(key, m.group())

        for m in _ACT_PATTERN.finditer(text):
            key = m.group().lower()
            found.setdefault(key, m.group())

        return list(found.values())

    def verify_citations_grounded(
        self,
        answer: str,
        context_chunks: list[dict],
    ) -> dict:
        """
        For every citation extracted from *answer*, check whether it
        (case-insensitively) appears in any chunk's ``text`` or
        ``source_name``.

        Returns a dict with keys:
            citations_found_in_answer, citations_grounded,
            citations_ungrounded, grounding_ratio
        """
        citations = self.extract_citations(answer)

        if not citations:
            return {
                "citations_found_in_answer": [],
                "citations_grounded": [],
                "citations_ungrounded": [],
                "grounding_ratio": 1.0,  # nothing to hallucinate
            }

        # Build a single lower-cased corpus string for fast substring search
        corpus_parts: list[str] = []
        for chunk in context_chunks:
            corpus_parts.append(chunk.get("text", "").lower())
            corpus_parts.append(chunk.get("source_name", "").lower())
        corpus = " ".join(corpus_parts)

        grounded: list[str] = []
        ungrounded: list[str] = []

        for citation in citations:
            if citation.lower() in corpus:
                grounded.append(citation)
            else:
                ungrounded.append(citation)

        total = len(citations)
        grounding_ratio = len(grounded) / total if total else 1.0

        return {
            "citations_found_in_answer": citations,
            "citations_grounded": grounded,
            "citations_ungrounded": ungrounded,
            "grounding_ratio": round(grounding_ratio, 3),
        }

    def compute_lexical_overlap(
        self,
        answer: str,
        context_chunks: list[dict],
    ) -> float:
        """
        Keyword-overlap ratio between *answer* and all *context_chunks*.

        Returns 0.0 on empty input (never raises ZeroDivisionError).
        """
        if not context_chunks:
            return 0.0

        answer_words = self._tokenize(answer)
        if not answer_words:
            return 0.0

        context_text = " ".join(chunk.get("text", "") for chunk in context_chunks)
        context_words = self._tokenize(context_text)

        overlap = answer_words & context_words
        return round(len(overlap) / len(answer_words), 3)

    def check(
        self,
        answer: str,
        context_chunks: list[dict],
    ) -> dict:
        """
        Main entry point.  Runs both checks and returns a single
        confidence assessment dict with 6 fields:

            grounding_ratio, lexical_overlap,
            citations_found, citations_ungrounded,
            confidence ("high" | "medium" | "low"),
            warning (str | None)
        """
        citation_result = self.verify_citations_grounded(answer, context_chunks)
        lexical_overlap = self.compute_lexical_overlap(answer, context_chunks)

        grounding_ratio     = citation_result["grounding_ratio"]
        citations_found     = citation_result["citations_found_in_answer"]
        citations_ungrounded = citation_result["citations_ungrounded"]

        # ── Confidence tiers ─────────────────────────────────────────
        # Recalibrated thresholds — grounding_ratio alone was too strict
        if grounding_ratio == 0.0 and lexical_overlap < 0.10:
            confidence = "low"
            warning = (
                "This response contains citations that could not "
                "be verified against the retrieved legal documents. "
                "Please verify independently."
            )
        elif grounding_ratio < 0.3 and lexical_overlap < 0.25:
            confidence = "low"
            warning = (
                "This response may not be well-grounded in the "
                "retrieved legal context. Please verify independently."
            )
        elif citations_ungrounded or lexical_overlap < 0.35:
            confidence = "medium"
            warning = None
        else:
            confidence = "high"
            warning = None

        print(
            f"[HALLUCINATION-CHECK] grounding={grounding_ratio:.2f} "
            f"lexical_overlap={lexical_overlap:.2f} "
            f"confidence={confidence}"
        )

        return {
            "grounding_ratio": grounding_ratio,
            "lexical_overlap": lexical_overlap,
            "citations_found": citations_found,
            "citations_ungrounded": citations_ungrounded,
            "confidence": confidence,
            "warning": warning,
        }
