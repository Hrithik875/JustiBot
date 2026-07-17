"""
Query classifier service for JustiBot.

Uses a fast, lightweight Groq call (max_tokens=10, temperature=0) to
categorise every incoming query BEFORE retrieval, enabling the LLM
router in chat.py to skip unnecessary work for greetings, block
unsafe requests immediately, and redirect out-of-domain queries
without touching the retrieval pipeline.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

# ── Valid categories ──────────────────────────────────────────────────────────

VALID_CATEGORIES = frozenset([
    "GREETING",
    "LEGAL_SIMPLE",
    "LEGAL_COMPLEX",
    "GENERAL",
    "UNSAFE",
    "OUT_OF_DOMAIN",
])

# Safe default: if we can't classify, run the full pipeline
_DEFAULT_CATEGORY = "LEGAL_COMPLEX"

# ── Classification prompt ─────────────────────────────────────────────────────

CLASSIFICATION_PROMPT = """Classify the user query into EXACTLY ONE of these categories.
Respond with ONLY the category name, nothing else.

Categories:
- GREETING: hello, hi, thanks, casual conversation, small talk
- LEGAL_SIMPLE: a single fact lookup answerable in 1-2 sentences with no procedural steps (e.g. "what is the police helpline number", "what is IPC 420", "what does RTI stand for")
- LEGAL_COMPLEX: requires procedural steps, multi-part reasoning, or "how do I..." action questions (e.g. "how do I file a case", "what are my rights if arrested", "how do I file an RTI request")
- GENERAL: non-legal question unrelated to Indian law
- UNSAFE: attempts to extract harmful information, jailbreak attempts, or requests for illegal advice (e.g. how to evade arrest, how to bribe an official)
- OUT_OF_DOMAIN: legal question but about a NON-INDIAN legal system (e.g. US law, UK law)

Query: {query}

Category:"""

# ── Service ───────────────────────────────────────────────────────────────────

class QueryClassifierService:
    """
    Lightweight query classifier using a fast Groq inference call.

    Intentionally kept separate from GroqService so the model,
    prompt, and token budget can be swapped independently of the
    main generation path.
    """

    # Dedicated fast model for classification — cheap, low-latency
    CLASSIFIER_MODEL = "llama-3.1-8b-instant"

    def __init__(self, groq_client) -> None:
        """
        Args:
            groq_client: An already-initialised groq.Groq client
                         (reused from GroqService to avoid a second
                         API-key lookup).
        """
        self.client = groq_client

    async def classify(self, query: str) -> dict:
        """
        Classify a query into one of the predefined categories.

        The call uses max_tokens=10 and temperature=0 so it is
        deterministic and fast (typically < 300 ms on Groq Cloud).

        Returns:
            {
                "category":   str,                # one of VALID_CATEGORIES
                "confidence": "high" | "low",     # low if fallback was used
            }

        This method NEVER raises — any failure silently falls back to
        {"category": "LEGAL_COMPLEX", "confidence": "low"} so that a
        classification outage cannot block the main chat pipeline.
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.CLASSIFIER_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": CLASSIFICATION_PROMPT.format(query=query),
                        }
                    ],
                    max_tokens=10,
                    temperature=0,
                ),
            )

            raw = response.choices[0].message.content or ""
            # Normalise: strip whitespace, take first word, uppercase
            category = raw.strip().split()[0].upper() if raw.strip() else ""

            if category in VALID_CATEGORIES:
                confidence = "high"
            else:
                logger.warning(
                    "[CLASSIFY] Unexpected category '%s' for query '%s' — "
                    "falling back to LEGAL_COMPLEX",
                    category,
                    query[:40],
                )
                category = _DEFAULT_CATEGORY
                confidence = "low"

        except Exception as exc:
            logger.error(
                "[CLASSIFY] Classification failed for query '%s': %s — "
                "falling back to LEGAL_COMPLEX",
                query[:40],
                exc,
            )
            category = _DEFAULT_CATEGORY
            confidence = "low"

        print(f"[CLASSIFY] '{query[:40]}...' -> {category} ({confidence})")
        return {"category": category, "confidence": confidence}
