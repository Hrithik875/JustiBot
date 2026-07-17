"""
Custom lightweight evaluation metrics for JustiBot Phase 4.

Inspired by RAGAS but computed entirely locally — no external library,
no LLM-judge API calls per metric.  This avoids the cost and latency
of running a separate grader model for every (test case × metric) pair
at portfolio-project scale.

All five metrics return a float in [0.0, 1.0].

Metric overview
───────────────
  keyword_coverage     — were required keywords/citations present in the answer?
  context_precision    — did retrieval surface documents from the right category?
  context_recall_proxy — does the context contain enough info to ground the answer?
  answer_relevance     — does the answer address the query's key terms?
  faithfulness         — is the answer grounded in retrieved context? (uses hallucination check output)
"""

import re
import string


# ---------------------------------------------------------------------------
# Internal tokeniser — same stopword set as hallucination_checker_service
# so recall-proxy reuses the same lexical-overlap logic.
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


def _tokenize(text: str) -> set[str]:
    """
    Lowercase, strip punctuation, split on whitespace, remove stopwords
    and very-short tokens (≤ 3 chars).

    Mirrors the logic in HallucinationCheckerService._tokenize() so that
    context_recall_proxy uses the same overlap computation as the live
    hallucination checker — making the two metrics directly comparable.
    """
    translator = str.maketrans("", "", string.punctuation)
    words = text.lower().translate(translator).split()
    return {w for w in words if len(w) > 3 and w not in _STOPWORDS}


# ---------------------------------------------------------------------------
# Metric 1 — Keyword Coverage
# ---------------------------------------------------------------------------

def keyword_coverage(answer: str, must_contain_keywords: list[str]) -> float:
    """
    Fraction of required keywords/citations present in the answer.

    Uses case-insensitive substring match (not tokenisation) so that
    exact strings like "1930" or "cybercrime.gov.in" are checked verbatim.

    Returns:
        1.0  if must_contain_keywords is empty (nothing to fail on)
        0.0–1.0 based on how many keywords were found
    """
    if not must_contain_keywords:
        return 1.0

    answer_lower = answer.lower()
    hits = sum(1 for kw in must_contain_keywords if kw.lower() in answer_lower)
    return hits / len(must_contain_keywords)


# ---------------------------------------------------------------------------
# Metric 2 — Context Precision
# ---------------------------------------------------------------------------

def context_precision(context_chunks: list[dict], expected_topic: str) -> float:
    """
    Fraction of retrieved chunks whose ``category`` field matches
    *expected_topic*.

    Measures: did retrieval fetch documents from the right legal domain?
    A high score means the hybrid search + reranker pulled relevant chunks.
    A low score (especially for out-of-scope topics like 'inheritance' or
    'patents') proves the metric is meaningful — retrieval cannot find what
    is not in the corpus.

    The match is case-insensitive substring so "cyber" matches "cyber" and
    "criminal" matches "criminal", etc.

    Returns:
        1.0 if no chunks were retrieved (nothing wrong to penalise)
    """
    if not context_chunks:
        return 1.0

    if not expected_topic:
        return 1.0

    topic_lower = expected_topic.lower()
    matching = sum(
        1 for chunk in context_chunks
        if topic_lower in chunk.get("category", "").lower()
    )
    return matching / len(context_chunks)


# ---------------------------------------------------------------------------
# Metric 3 — Context Recall Proxy
# ---------------------------------------------------------------------------

def context_recall_proxy(
    context_chunks: list[dict],
    ground_truth_answer: str,
) -> float:
    """
    Lexical overlap between the *ground_truth_answer* and the combined
    retrieved context text.

    Proxy question: did retrieval surface enough information to allow the
    LLM to construct the correct answer?  High overlap → likely yes.
    Low overlap → retrieval missed key facts.

    Reuses the same tokenise + set-intersection logic as
    HallucinationCheckerService.compute_lexical_overlap(), with roles
    reversed: here we measure how much of the *ground truth* vocabulary
    is covered by the *context*, rather than how much of the *answer*
    is covered by the *context*.

    Returns:
        0.0 if no ground_truth_answer or no chunks
    """
    if not ground_truth_answer or not context_chunks:
        return 0.0

    gt_words = _tokenize(ground_truth_answer)
    if not gt_words:
        return 0.0

    context_text = " ".join(chunk.get("text", "") for chunk in context_chunks)
    context_words = _tokenize(context_text)

    overlap = gt_words & context_words
    return round(len(overlap) / len(gt_words), 3)


# ---------------------------------------------------------------------------
# Metric 4 — Answer Relevance
# ---------------------------------------------------------------------------

def answer_relevance(answer: str, query: str) -> float:
    """
    Simple relevance proxy: keyword overlap between the query's significant
    terms and the generated answer.

    Not semantic similarity (that would require an embedding call) — pure
    lexical overlap.  Directionally useful: if the answer contains none of
    the query's key terms it is very likely off-topic.

    Returns:
        0.0 if the query has no significant terms after stopword removal
    """
    query_words = _tokenize(query)
    if not query_words:
        return 0.0

    answer_words = _tokenize(answer)
    if not answer_words:
        return 0.0

    overlap = query_words & answer_words
    # Normalise by query length so a short, focused query isn't penalised
    # for an answer that contains extra vocabulary.
    return round(len(overlap) / len(query_words), 3)


# ---------------------------------------------------------------------------
# Metric 5 — Faithfulness (from hallucination checker)
# ---------------------------------------------------------------------------

def faithfulness_from_checker(hallucination_check: dict) -> float:
    """
    Converts the existing HallucinationCheckerService output into a
    numeric faithfulness score.

    Mapping (chosen to be interpretable and monotonic):
        "high"   → 1.0   (citations grounded, good lexical overlap)
        "medium" → 0.6   (some ungrounded citations or borderline overlap)
        "low"    → 0.2   (poor grounding — likely hallucination)

    Args:
        hallucination_check: The dict returned by HallucinationCheckerService.check()

    Returns:
        float in {0.2, 0.6, 1.0}
    """
    confidence = hallucination_check.get("confidence", "low")
    mapping = {
        "high": 1.0,
        "medium": 0.6,
        "low": 0.2,
    }
    return mapping.get(confidence, 0.2)
