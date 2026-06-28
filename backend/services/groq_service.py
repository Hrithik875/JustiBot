"""
Groq LLM service for JustiBot.
"""

import asyncio
import logging
import groq
from fastapi import HTTPException
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

MAX_CONTEXT_CHARS = 3000


class GroqService:

    MODEL_NAME = "llama-3.1-8b-instant"

    def __init__(self):
        self.client = groq.Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = self.MODEL_NAME

    async def generate(
        self,
        query: str,
        context_chunks: list[dict],
        conversation_history: list[dict] = []
    ) -> dict:

        # a) Build context string
        sorted_chunks = sorted(
            context_chunks, key=lambda x: x["score"], reverse=True
        )

        if not sorted_chunks:
            context_str = "No specific legal documents found for this query."
        else:
            chunk_strs = [
                f"[Source: {chunk['source_name']}]\n{chunk['text']}\n"
                for chunk in sorted_chunks
            ]
            context_str = "\n---\n".join(chunk_strs)

        # Truncate context to prevent empty responses from context overflow
        if len(context_str) > MAX_CONTEXT_CHARS:
            context_str = (
                context_str[:MAX_CONTEXT_CHARS] + "\n...[context truncated]"
            )

        # b) Build messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"LEGAL CONTEXT FROM OFFICIAL DOCUMENTS:\n{context_str}\n\n"
                    f"---\n\n"
                    f"USER QUERY: {query}\n\n"
                    f"Instructions: Answer based on the legal context provided "
                    f"above. Cite specific sections, articles, or acts by name "
                    f"when referencing them. If the context doesn't fully cover "
                    f"the query, say so clearly and recommend consulting a lawyer. "
                    f"Format your response with clear headings using markdown. "
                    f"If relevant helpline numbers apply to this situation, "
                    f"include them highlighted."
                )
            }
        ]

        if conversation_history:
            messages.extend(conversation_history[-4:])

        # c) Call Groq API with retry for empty responses
        MAX_RETRIES = 2
        answer = ""

        for attempt in range(MAX_RETRIES):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=2048,
                        top_p=0.9,
                    )
                )
                answer = response.choices[0].message.content

                if answer and len(answer.strip()) > 0:
                    logging.info(f"Groq responded on attempt {attempt + 1}")
                    break
                else:
                    logging.warning(
                        f"Groq returned empty answer on attempt "
                        f"{attempt + 1}/{MAX_RETRIES} — retrying..."
                    )
                    await asyncio.sleep(2)

            except groq.RateLimitError:
                if attempt < MAX_RETRIES - 1:
                    logging.warning(
                        f"Groq rate limit on attempt {attempt + 1} "
                        f"— waiting 10s"
                    )
                    await asyncio.sleep(10)
                    continue
                raise HTTPException(
                    429,
                    "You've reached the AI service limit. "
                    "Please wait a minute and try again."
                )
            except groq.APIError as e:
                logging.error(f"Groq APIError: {e}")
                raise HTTPException(502, "LLM service temporarily unavailable.")
            except Exception as e:
                logging.error(f"Groq generation failed: {e}")
                raise HTTPException(500, f"Failed to generate response: {e}")

        if not answer or len(answer.strip()) == 0:
            logging.error("Groq returned empty answer after all retries")
            raise HTTPException(
                502,
                "The AI service returned an empty response. Please try again."
            )

        # d) Build deduplicated sources list
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

        # e) Return response dict
        return {
            "answer": answer,
            "sources": sources,
            "model": self.model_name,
            "context_chunks_used": len(context_chunks)
        }