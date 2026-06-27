"""
Chat endpoints for JustiBot API.
Full RAG pipeline with Redis caching, semantic cache, and Firestore persistence.
"""
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from backend.middleware.auth import verify_firebase_token
from backend.middleware.security import validate_query
from backend.corpus.embedder import Embedder
from backend.services.qdrant_service import QdrantService
from backend.services.redis_service import RedisService
from backend.services.groq_service import GroqService
from backend.services.firestore_service import FirestoreService

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Service singletons ────────────────────────────────────────────────────────
embedder = Embedder()
qdrant = QdrantService()
redis = RedisService()
groq_svc = GroqService()
firestore_svc = FirestoreService()


# ── Utilities ─────────────────────────────────────────────────────────────────

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


# ── Request models ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""
    query: str
    session_id: str
    category_filter: str | None = None
    conversation_history: list[dict] = []
    is_new_session: bool = False

    @field_validator('conversation_history')
    @classmethod
    def limit_history(cls, v):
        return v[-10:]

    class Config:
        pass


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    request: ChatRequest,
    token: dict = Depends(verify_firebase_token),
) -> dict:
    """
    Full RAG pipeline:
      1. Validate input
      2a. Exact cache lookup
      2b. Semantic cache lookup
      3. Embed query (only if cache missed)
      4. Qdrant semantic search
      5. Groq LLM generation
      6. Cache result (exact + semantic)
      6.5. Firestore persistence (non-fatal)
      7. Return response
    """
    # STEP 1 — Validate and sanitize input
    clean_query = validate_query(request.query)
    user_uid = token["uid"]

    # STEP 2A — Exact cache check
    cache_key = redis.make_cache_key(clean_query)
    cached = await redis.get_cached(cache_key)
    if cached:
        cached["cached"] = True
        cached["session_id"] = request.session_id
        cached["user_uid"] = user_uid
        return cached

    # STEP 2B — Semantic cache check (also produces the embedding for STEP 4)
    query_embedding = embedder.embed_query(clean_query)
    semantic_match = await redis.find_semantic_match(query_embedding)
    if semantic_match:
        semantic_match["cached"] = True
        semantic_match["semantic_cache"] = True
        semantic_match["session_id"] = request.session_id
        semantic_match["user_uid"] = user_uid
        return semantic_match

    # STEP 3 — Embedding already computed in STEP 2B; skip re-embedding

    # STEP 4 — Search Qdrant
    context_chunks = qdrant.search(
        query_embedding=query_embedding,
        category_filter=request.category_filter,
        limit=5,
    )

    # STEP 5 — Generate response via Groq
    result = await groq_svc.generate(
        query=clean_query,
        context_chunks=context_chunks,
        conversation_history=request.conversation_history,
    )

    # Apply response formatting
    formatted_answer = format_response_links(result["answer"])

    # STEP 6 — Cache the result (exact + semantic)
    response_to_cache = {
        "answer": formatted_answer,
        "sources": result["sources"],
        "model": result["model"],
        "context_chunks_used": result["context_chunks_used"],
        "cached": False,
    }
    await redis.set_cached(cache_key, response_to_cache)
    await redis.store_semantic_key(
        query=clean_query,
        embedding=query_embedding,
        cache_key=cache_key,
    )

    # STEP 6.5 — Persist to Firestore (non-fatal)
    try:
        if request.is_new_session:
            await firestore_svc.create_session(
                user_uid=user_uid,
                session_id=request.session_id,
                first_message=clean_query,
            )

        await firestore_svc.save_message(
            user_uid=user_uid,
            session_id=request.session_id,
            role="user",
            content=clean_query,
        )
        await firestore_svc.save_message(
            user_uid=user_uid,
            session_id=request.session_id,
            role="assistant",
            content=result["answer"],
            sources=result["sources"],
            cached=response_to_cache["cached"],
        )
    except Exception as exc:
        logger.error("[FIRESTORE] Persistence failed for session=%s: %s", request.session_id, exc)

    # STEP 7 — Return response
    return {
        **response_to_cache,
        "session_id": request.session_id,
        "cached": False,
        "user_uid": user_uid,
    }


# ── Session endpoints ─────────────────────────────────────────────────────────

@router.get("/chat/sessions")
async def get_sessions(
    token: dict = Depends(verify_firebase_token),
) -> dict:
    """Return all chat sessions for the authenticated user, newest first."""
    sessions = await firestore_svc.get_sessions(token["uid"])
    return {"sessions": sessions, "count": len(sessions)}


@router.get("/chat/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = 20,
    token: dict = Depends(verify_firebase_token),
) -> dict:
    """Return all messages for a session. Requires session ownership."""
    session = await firestore_svc.get_session(token["uid"], session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await firestore_svc.get_messages(token["uid"], session_id, limit)
    return {"session": session, "messages": messages, "count": len(messages)}


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    token: dict = Depends(verify_firebase_token),
) -> dict:
    """Delete a session and all its messages."""
    deleted = await firestore_svc.delete_session(token["uid"], session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True, "session_id": session_id}


@router.patch("/chat/sessions/{session_id}/title")
async def update_session_title(
    session_id: str,
    body: dict,
    token: dict = Depends(verify_firebase_token),
) -> dict:
    """Rename a chat session."""
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if len(title) > 100:
        raise HTTPException(status_code=400, detail="Title too long (max 100 chars)")

    await firestore_svc.update_session_title(token["uid"], session_id, title)
    return {"updated": True, "session_id": session_id, "title": title}
