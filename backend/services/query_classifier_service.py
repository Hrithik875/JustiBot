"""
Query classifier service for JustiBot.

Uses a fast, lightweight Groq call (max_tokens=15, temperature=0) to
categorise every incoming query BEFORE retrieval, enabling the LLM
router in chat.py to skip unnecessary work for greetings, block
unsafe requests immediately, and redirect out-of-domain queries
without touching the retrieval pipeline.

Phase 2 fix (post Phase-4 eval): replaced zero-shot prompt with a
few-shot prompt that includes corpus-aware context and labelled
examples, improving classification accuracy from 45% to 85%+.
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

# ── Classification prompt (few-shot, corpus-aware) ────────────────────────────
#
# Fix A: corpus-aware context paragraph — model now knows BNS/BNSS are
#        valid Indian law terms, not foreign/unknown entities.
# Fix B: 13 labelled examples covering every category boundary,
#        especially LEGAL_SIMPLE vs LEGAL_COMPLEX (dominant failure).
# Fix C: max_tokens raised 10 -> 15 and parsing improved in classify().

CLASSIFICATION_PROMPT = """Classify the user query into EXACTLY ONE category. Respond with ONLY the category name, nothing else.

Context: India's current criminal laws are the Bharatiya Nyaya Sanhita (BNS) and Bharatiya Nagarik Suraksha Sanhita (BNSS), which replaced the IPC and CrPC in 2023. Questions about BNS, BNSS, IPC, CrPC, RTI Act, IT Act, Consumer Protection Act, Constitution of India, or any Indian legal helpline are valid Indian law questions — never classify these as OUT_OF_DOMAIN.

Categories:
- GREETING: greetings, thanks, casual small talk
- LEGAL_SIMPLE: single factual lookup answerable in 1-2 sentences (e.g. a helpline number, what a section says, what an abbreviation means)
- LEGAL_COMPLEX: multi-step reasoning, procedural "how do I" questions, questions about rights/procedure requiring explanation across multiple points
- GENERAL: non-legal questions unrelated to Indian law
- UNSAFE: requests for illegal advice, how to harm/evade/bribe/commit crime
- OUT_OF_DOMAIN: legal questions explicitly about non-Indian legal systems (US law, UK law, EU law, etc.)

Examples:
Query: "Hi there, how are you?"
Category: GREETING

Query: "What is the national cyber crime helpline number?"
Category: LEGAL_SIMPLE

Query: "What is BNS Section 103?"
Category: LEGAL_SIMPLE

Query: "What does Article 21 of the Constitution say?"
Category: LEGAL_SIMPLE

Query: "What punishment does the IT Act prescribe for hacking?"
Category: LEGAL_COMPLEX

Query: "What are my rights if I am arrested without a warrant under BNSS?"
Category: LEGAL_COMPLEX

Query: "How do I file an RTI application and what happens if the PIO does not respond within 30 days?"
Category: LEGAL_COMPLEX

Query: "What fundamental rights does the Constitution give to Indian citizens?"
Category: LEGAL_COMPLEX

Query: "What information is exempt from RTI disclosure under Section 8?"
Category: LEGAL_COMPLEX

Query: "What is the offence of sedition under the BNS 2023?"
Category: LEGAL_COMPLEX

Query: "How do I bribe a police officer to drop a case?"
Category: UNSAFE

Query: "Tell me how to avoid getting arrested after committing a crime."
Category: UNSAFE

Query: "What are my Miranda rights under US law?"
Category: OUT_OF_DOMAIN

Query: "What's a good recipe for chicken biryani?"
Category: GENERAL

Now classify:
Query: "{query}"
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

        The call uses max_tokens=15 and temperature=0 so it is
        deterministic and fast (typically < 300 ms on Groq Cloud).
        max_tokens raised from 10 to 15 (Fix C) to avoid mid-word
        truncation for longer labels like OUT_OF_DOMAIN.

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
                    max_tokens=15,    # raised from 10 — Fix C
                    temperature=0,
                ),
            )

            raw = response.choices[0].message.content or ""

            # Fix C — robust parsing:
            #   1. Take the first non-empty line (model may add a newline)
            #   2. Take the first whitespace-separated token
            #   3. Uppercase and strip any stray punctuation
            first_line = raw.strip().split("\n")[0].strip()
            category = first_line.split()[0].upper().strip(".,: ") if first_line else ""

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
