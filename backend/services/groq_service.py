"""
Groq LLM service stub for JustiBot.
Phase 1: Structure only. Full RAG generation implemented in Phase 2.
"""

import groq

from backend.config import settings

SYSTEM_PROMPT = """
You are JustiBot, an expert Indian legal assistant. You help Indian
citizens understand their legal rights, laws, and procedures.

STRICT RULES:
1. Only answer questions related to Indian law, legal procedures,
   rights, and civic matters.
2. Always cite the specific Act, Section, or Article you are
   referencing.
3. If you are unsure about something, say so explicitly.
   Never fabricate legal information.
4. Always recommend consulting a qualified lawyer for specific
   legal advice.
5. Format responses clearly with headings and bullet points
   where appropriate.
6. If a question involves emergency situations, always mention
   relevant helpline numbers.
7. Do not answer questions unrelated to legal matters.
   Politely redirect to legal topics.

You will be provided with relevant excerpts from official Indian
legal documents as context. Base your answer primarily on this
context.
"""


class GroqService:
    """
    Wrapper around the Groq API for LLM response generation.
    """

    MODEL_NAME = "llama-3.3-70b-versatile"

    def __init__(self):
        self.client = groq.Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = self.MODEL_NAME

    async def generate(
        self,
        query: str,
        context_chunks: list[dict],
        conversation_history: list[dict] = []
    ) -> dict:
        """
        Generate a legal response using retrieved context (RAG).
        """
        # a) Build context string from context_chunks
        sorted_chunks = sorted(context_chunks, key=lambda x: x["score"], reverse=True)
        
        if not sorted_chunks:
            context_str = "No specific legal documents found for this query."
        else:
            chunk_strs = [
                f"[Source: {chunk['source_name']}]\n{chunk['text']}\n"
                for chunk in sorted_chunks
            ]
            context_str = "\n---\n".join(chunk_strs)

        # b) Build the messages list for Groq
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""LEGAL CONTEXT FROM OFFICIAL DOCUMENTS:
{context_str}

---

USER QUERY: {query}

Instructions: Answer based on the legal context provided above.
Cite specific sections, articles, or acts by name when referencing
them. If the context doesn't fully cover the query, say so clearly
and recommend consulting a lawyer. Format your response with clear
headings using markdown. If relevant helpline numbers apply to this
situation, include them highlighted."""}
        ]

        if conversation_history:
            messages.extend(conversation_history[-6:])

        # c) Call Groq API
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                max_tokens=2048,
                top_p=0.9,
            )
        except groq.RateLimitError:
            from fastapi import HTTPException
            raise HTTPException(429, "Rate limit reached. Please wait a moment and try again.")
        except groq.APIError as e:
            import logging
            logging.error(f"Groq APIError: {e}")
            from fastapi import HTTPException
            raise HTTPException(502, "LLM service temporarily unavailable.")
        except Exception as e:
            import logging
            logging.error(f"Groq generation failed: {e}")
            from fastapi import HTTPException
            raise HTTPException(500, f"Failed to generate response: {e}")

        # d) Extract response text
        answer = response.choices[0].message.content

        # e) Build and return sources list
        seen_urls = set()
        sources = []
        for chunk in sorted_chunks:
            if chunk["source_url"] not in seen_urls:
                seen_urls.add(chunk["source_url"])
                sources.append({
                    "name": chunk["source_name"],
                    "url": chunk["source_url"],
                    "category": chunk["category"],
                    "relevance_score": round(chunk["score"], 3)
                })

        # f) Return dict
        return {
            "answer": answer,
            "sources": sources,
            "model": self.model_name,
            "context_chunks_used": len(context_chunks)
        }
