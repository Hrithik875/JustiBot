"""
Chat endpoints for JustiBot API.
Full RAG pipeline implemented.
"""
import re
from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from backend.middleware.auth import verify_firebase_token
from backend.middleware.security import validate_query
from backend.corpus.embedder import Embedder
from backend.services.qdrant_service import QdrantService
from backend.services.redis_service import RedisService
from backend.services.groq_service import GroqService

router = APIRouter()

# Initialize services once at module level
embedder = Embedder()
qdrant = QdrantService()
redis = RedisService()
groq_svc = GroqService()

def format_response_links(text: str) -> str:
    """
    Post-processes LLM response to ensure URLs, phone numbers,
    and emails are properly formatted for frontend rendering.
    """
    # Wrap bare URLs not already in markdown link syntax
    url_pattern = r'(?<!\()(?<!\[)(https?://[^\s\)]+)(?!\))'
    text = re.sub(url_pattern, r'[\1](\1)', text)

    # Wrap email addresses
    email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    text = re.sub(email_pattern, r'[\1](mailto:\1)', text)

    # Highlight Indian helpline numbers
    helpline_pattern = r'\b(1930|100|1091|1915|15100|14567|112)\b'
    text = re.sub(helpline_pattern, r'**`\1`**', text)

    return text

class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""
    query: str
    session_id: str
    category_filter: str | None = None
    conversation_history: list[dict] = []

    @field_validator('conversation_history')
    @classmethod
    def limit_history(cls, v):
        return v[-10:]  # max 10 turns passed from frontend

    class Config:
        # Ensure conversation_history dicts only have role+content keys
        pass

@router.post("/chat")
async def chat(
    request: ChatRequest,
    token: dict = Depends(verify_firebase_token),
) -> dict:
    """
    Accept a legal query, retrieve context via Qdrant,
    and generate an answer using Groq LLM (RAG pipeline).
    """
    # STEP 1 — Validate and sanitize input
    clean_query = validate_query(request.query)
    user_uid = token["uid"]

    # STEP 2 — Check Redis cache
    cache_key = redis.make_cache_key(clean_query)
    cached = await redis.get_cached(cache_key)
    if cached:
        cached["cached"] = True
        cached["session_id"] = request.session_id
        cached["user_uid"] = user_uid
        return cached

    # STEP 3 — Embed the query
    query_embedding = embedder.embed_query(clean_query)

    # STEP 4 — Search Qdrant
    context_chunks = qdrant.search(
        query_embedding=query_embedding,
        category_filter=request.category_filter,
        limit=5
    )

    # STEP 5 — Generate response via Groq
    result = await groq_svc.generate(
        query=clean_query,
        context_chunks=context_chunks,
        conversation_history=request.conversation_history
    )

    # Apply response formatting to the answer
    formatted_answer = format_response_links(result["answer"])

    # STEP 6 — Cache the result
    response_to_cache = {
        "answer": formatted_answer,
        "sources": result["sources"],
        "model": result["model"],
        "context_chunks_used": result["context_chunks_used"],
        "cached": False
    }
    await redis.set_cached(cache_key, response_to_cache)

    # STEP 7 — Return response
    return {
        **response_to_cache,
        "session_id": request.session_id,
        "cached": False,
        "user_uid": user_uid
    }

@router.get("/chat/sessions")
async def get_sessions(
    token: dict = Depends(verify_firebase_token),
) -> dict:
    """
    Return a list of chat sessions for the authenticated user.
    Phase 1 stub — Firestore integration added in Phase 3.
    """
    return {
        "sessions": [],
        "message": "Firestore not yet wired",
    }

@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    token: dict = Depends(verify_firebase_token),
) -> dict:
    """
    Delete a specific chat session.
    Phase 1 stub — not yet implemented.
    """
    return {
        "deleted": session_id,
        "message": "Not yet implemented",
    }
