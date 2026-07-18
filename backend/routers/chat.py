"""
Chat endpoints for JustiBot API.
Full RAG pipeline with Redis caching, semantic cache, Firestore persistence,
hybrid BM25+dense retrieval, cross-encoder reranking, query classification,
and 2-tier LLM routing.
"""
import asyncio
import logging
import re
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from backend.middleware.auth import verify_firebase_token
from backend.middleware.security import validate_query
from backend.corpus.embedder import Embedder
from backend.services.qdrant_service import QdrantService
from backend.services.redis_service import RedisService
from backend.services.groq_service import GroqService
from backend.services.firestore_service import FirestoreService
from backend.services.bm25_service import BM25Service
from backend.services.hybrid_search_service import HybridSearchService
from backend.services.reranker_service import RerankerService
from backend.services.query_classifier_service import QueryClassifierService
from backend.services.hallucination_checker_service import HallucinationCheckerService
from backend.services.observability_service import ObservabilityService, estimate_cost

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Service singletons ────────────────────────────────────────────────────────
embedder = Embedder()
qdrant = QdrantService()
redis = RedisService()
groq_svc = GroqService()
firestore_svc = FirestoreService()

# Hybrid retrieval + reranking services (loaded once at startup)
bm25_svc = BM25Service(qdrant)
hybrid_search_svc = HybridSearchService(qdrant, bm25_svc)
reranker_svc = RerankerService()

# Query classifier — reuses groq_svc's already-initialised client
query_classifier_svc = QueryClassifierService(groq_svc.client)

# Hallucination checker — pure text analysis, no model loading
hallucination_checker_svc = HallucinationCheckerService()

# Observability — records per-request pipeline timings to Redis
observability_svc = ObservabilityService(redis)

MIN_ANSWER_LENGTH = 100
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

    # Highlight Indian helpline numbers with backtick formatting
    helpline_pattern = r'\b(1930|100|1091|1915|15100|14567|112)\b'
    text = re.sub(helpline_pattern, r'`\1`', text)

    return text


# ── Request models ────────────────────────────────────────────────────────────

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
      1.   Validate input
      1.5. Classify query → route (UNSAFE / OUT_OF_DOMAIN handled immediately)
      2a.  Exact cache lookup
      2b.  Semantic cache lookup
      3.   Embed query (only if cache missed)
      4.   Hybrid retrieval (dense + BM25 sparse → RRF fusion) + cross-encoder
           reranking  [skipped entirely for GREETING]
      5.   Groq LLM generation (routed by query category)
      5.5. Hallucination check (LEGAL_SIMPLE / LEGAL_COMPLEX only)
      6.   Cache result (exact + semantic)
      6.5. Firestore persistence (non-fatal)
      7.   Return response
    """
    # Minimum delay between Groq calls to prevent empty responses
    # on consecutive requests (free tier behavior with 70b model)
    await asyncio.sleep(4)

    # ── Observability: timing collector ──────────────────────────────────────
    timings: dict[str, float] = {}
    retrieval_broadened = False

    # STEP 1 — Validate and sanitize input
    clean_query = validate_query(request.query)
    user_uid = token["uid"]

    # STEP 1.5 — Classify query and route
    t0 = time.perf_counter()
    classification = await query_classifier_svc.classify(clean_query)
    timings["classification"] = (time.perf_counter() - t0) * 1000
    category = classification["category"]

    async def _persist_chat(answer_text: str, sources_list: list, model_name: str, is_cached: bool):
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
                content=answer_text,
                sources=sources_list,
                cached=is_cached,
                model=model_name,
            )
        except Exception as exc:
            logger.error("[FIRESTORE] Persistence failed: %s", exc)

    # UNSAFE: block immediately — no cache, no retrieval, no LLM call
    if category == "UNSAFE":
        logger.warning("[CLASSIFY] Blocked UNSAFE query: %s", clean_query[:50])
        unsafe_answer = (
            "I can't help with that request. JustiBot is designed "
            "to help you understand your legal rights and procedures "
            "under Indian law. If you're facing a legal issue, I'd "
            "encourage you to consult a qualified lawyer or contact "
            "the National Legal Services Authority helpline at `15100`."
        )
        await _persist_chat(unsafe_answer, [], "safety-filter", False)
        timings["total"] = sum(timings.values())
        asyncio.create_task(observability_svc.record_event({
            "timestamp": datetime.utcnow().isoformat(),
            "query_category": "UNSAFE",
            "model_used": "safety-filter",
            "cache_hit": False,
            "cache_type": None,
            "timings_ms": timings,
            "hallucination_confidence": "high",
            "estimated_cost_usd": 0.0,
        }, user_uid))
        return {
            "answer": unsafe_answer,
            "sources": [],
            "model": "safety-filter",
            "context_chunks_used": 0,
            "cached": False,
            "session_id": request.session_id,
            "user_uid": user_uid,
            "query_category": "UNSAFE",
        }

    # OUT_OF_DOMAIN: redirect politely — no retrieval or generation
    if category == "OUT_OF_DOMAIN":
        ood_answer = (
            "JustiBot specialises in Indian law and legal procedures. "
            "Your question appears to be about a different country's "
            "legal system, which I'm not equipped to answer accurately. "
            "For Indian legal matters — rights, procedures, or specific "
            "acts and sections — I'm happy to help."
        )
        await _persist_chat(ood_answer, [], "domain-filter", False)
        timings["total"] = sum(timings.values())
        asyncio.create_task(observability_svc.record_event({
            "timestamp": datetime.utcnow().isoformat(),
            "query_category": "OUT_OF_DOMAIN",
            "model_used": "domain-filter",
            "cache_hit": False,
            "cache_type": None,
            "timings_ms": timings,
            "hallucination_confidence": "high",
            "estimated_cost_usd": 0.0,
        }, user_uid))
        return {
            "answer": ood_answer,
            "sources": [],
            "model": "domain-filter",
            "context_chunks_used": 0,
            "cached": False,
            "session_id": request.session_id,
            "user_uid": user_uid,
            "query_category": "OUT_OF_DOMAIN",
        }

    # STEP 2A — Exact cache check
    cache_key = redis.make_cache_key(clean_query)
    cached = await redis.get_cached(cache_key)
    if cached:
        cached["cached"] = True
        cached["session_id"] = request.session_id
        cached["user_uid"] = user_uid
        cached.setdefault("query_category", category)
        await _persist_chat(cached["answer"], cached.get("sources", []), cached.get("model", "unknown"), True)
        timings["total"] = sum(timings.values())
        asyncio.create_task(observability_svc.record_event({
            "timestamp": datetime.utcnow().isoformat(),
            "query_category": category,
            "model_used": cached.get("model", "unknown"),
            "cache_hit": True,
            "cache_type": "exact",
            "timings_ms": timings,
            "hallucination_confidence": "high",
            "estimated_cost_usd": 0.0,
        }, user_uid))
        return cached

    # STEP 2B — Semantic cache check
    # Also produces the embedding reused in STEP 4
    t0 = time.perf_counter()
    query_embedding = embedder.embed_query(clean_query)
    timings["embedding"] = (time.perf_counter() - t0) * 1000

    semantic_match = await redis.find_semantic_match(query_embedding)
    if semantic_match:
        semantic_match["cached"] = True
        semantic_match["semantic_cache"] = True
        semantic_match["session_id"] = request.session_id
        semantic_match["user_uid"] = user_uid
        semantic_match.setdefault("query_category", category)
        await _persist_chat(semantic_match["answer"], semantic_match.get("sources", []), semantic_match.get("model", "unknown"), True)
        timings["total"] = sum(timings.values())
        asyncio.create_task(observability_svc.record_event({
            "timestamp": datetime.utcnow().isoformat(),
            "query_category": category,
            "model_used": semantic_match.get("model", "unknown"),
            "cache_hit": True,
            "cache_type": "semantic",
            "timings_ms": timings,
            "hallucination_confidence": "high",
            "estimated_cost_usd": 0.0,
        }, user_uid))
        return semantic_match

    # STEP 3 — Embedding already computed in STEP 2B

    # STEP 4 — Hybrid retrieval (dense + sparse fusion) + reranking
    # GREETINGs skip retrieval entirely — they don't need legal context.
    if category == "GREETING":
        context_chunks = []
        _retrieval_debug = {
            "dense_candidates": 0,
            "sparse_candidates": 0,
            "fused_candidates": 0,
            "reranked_to": 0,
            "skipped": "GREETING category",
        }
    else:
        t0 = time.perf_counter()
        fused_candidates = hybrid_search_svc.search(
            query=clean_query,
            query_embedding=query_embedding,
            category_filter=request.category_filter,
            limit=30,
        )
        timings["hybrid_search"] = (time.perf_counter() - t0) * 1000

        _dense_count = sum(1 for c in fused_candidates if c["dense_rank"] is not None)
        _sparse_count = sum(1 for c in fused_candidates if c["sparse_rank"] is not None)
        _fused_count = len(fused_candidates)

        t0 = time.perf_counter()
        context_chunks = reranker_svc.rerank(
            query=clean_query,
            candidates=fused_candidates,
            top_k=5,
        )
        timings["reranking"] = (time.perf_counter() - t0) * 1000

        # Map rerank_score → score so groq_svc.generate() (which sorts by "score")
        # continues to work without modification.
        for chunk in context_chunks:
            chunk["score"] = chunk["rerank_score"]

        # STEP 4.5 — Confidence-gated broadened retry (bounded to ONE
        # extra pass, never loops further)
        if reranker_svc.is_retrieval_weak(context_chunks):
            print(
                f"[RETRIEVAL] Weak initial retrieval (top score="
                f"{context_chunks[0].get('score', 0.0) if context_chunks else 0.0:.3f}) — "
                "broadening search once"
            )
            t0 = time.perf_counter()
            fused_broad = hybrid_search_svc.search_broadened(
                query=clean_query,
                query_embedding=query_embedding,
                limit=50,
            )
            broadened_reranked = reranker_svc.rerank(
                clean_query, fused_broad, top_k=5,
            )
            timings["broadened_retry"] = (time.perf_counter() - t0) * 1000

            # Map rerank_score → score on broadened results too
            for chunk in broadened_reranked:
                chunk["score"] = chunk["rerank_score"]

            # Only USE the broadened results if they're actually better
            if (
                broadened_reranked
                and broadened_reranked[0].get("score", 0.0)
                > (context_chunks[0].get("score", 0.0) if context_chunks else 0.0)
            ):
                context_chunks = broadened_reranked
                retrieval_broadened = True
                print(
                    f"[RETRIEVAL] Broadened search improved top score to {context_chunks[0]['score']:.3f}"
                )
            else:
                print(
                    "[RETRIEVAL] Broadened search did not improve results — keeping original"
                )

        _retrieval_debug = {
            "dense_candidates": _dense_count,
            "sparse_candidates": _sparse_count,
            "fused_candidates": _fused_count,
            "reranked_to": len(context_chunks),
        }

    # STEP 5 — Generate response (routed by query category)
    t0 = time.perf_counter()
    if category == "GREETING":
        result = await groq_svc.generate_simple(
            query=clean_query,
            context_chunks=[],
        )
    elif category == "LEGAL_SIMPLE":
        result = await groq_svc.generate_simple(
            query=clean_query,
            context_chunks=context_chunks,
        )
    else:  # LEGAL_COMPLEX, GENERAL, or low-confidence fallback
        result = await groq_svc.generate(
            query=clean_query,
            context_chunks=context_chunks,
            conversation_history=request.conversation_history,
        )
    timings["generation"] = (time.perf_counter() - t0) * 1000

    # STEP 5.5 — Hallucination check
    # Only meaningful for answers grounded in retrieved legal context.
    # Greetings, safety blocks, and domain redirects skip this.
    t0 = time.perf_counter()
    if category in ("LEGAL_SIMPLE", "LEGAL_COMPLEX"):
        hallucination_check = hallucination_checker_svc.check(
            answer=result["answer"],
            context_chunks=context_chunks,
        )
    else:
        hallucination_check = {
            "confidence": "high",
            "warning": None,
            "grounding_ratio": 1.0,
            "lexical_overlap": 1.0,
            "citations_found": [],
            "citations_ungrounded": [],
        }
    timings["hallucination_check"] = (time.perf_counter() - t0) * 1000

    # Apply response link formatting
    formatted_answer = format_response_links(result["answer"])

    # Prepend a visible warning banner when confidence is low so the
    # caution is present even if the frontend doesn’t render the
    # hallucination_check metadata field yet.
    if hallucination_check["confidence"] == "low" and hallucination_check["warning"]:
        formatted_answer = (
            f"⚠️ *{hallucination_check['warning']}*\n\n{formatted_answer}"
        )

    # STEP 6 — Cache the result
    # Only cache non-empty answers — never cache empty responses
    if formatted_answer and len(formatted_answer.strip()) >= MIN_ANSWER_LENGTH:
        response_to_cache = {
            "answer": formatted_answer,
            "sources": result["sources"],
            "model": result["model"],
            "context_chunks_used": result["context_chunks_used"],
            "cached": False,
            "retrieval_debug": _retrieval_debug,
            "query_category": category,
            "hallucination_check": hallucination_check,
            "retrieval_broadened": retrieval_broadened,
        }
        await redis.set_cached(cache_key, response_to_cache)
        await redis.store_semantic_key(
            query=clean_query,
            embedding=query_embedding,
            cache_key=cache_key,
        )
    else:
        logger.warning(
            "Empty answer from Groq for query: %s", clean_query[:50]
        )
        response_to_cache = {
            "answer": formatted_answer,
            "sources": result["sources"],
            "model": result["model"],
            "context_chunks_used": result["context_chunks_used"],
            "cached": False,
            "retrieval_debug": _retrieval_debug,
            "query_category": category,
            "hallucination_check": hallucination_check,
            "retrieval_broadened": retrieval_broadened,
        }

    # STEP 6.5 — Persist to Firestore (non-fatal)
    await _persist_chat(formatted_answer, result["sources"], result["model"], False)

    # ── Observability: record pipeline event (fire-and-forget) ────────────
    timings["total"] = sum(timings.values())
    asyncio.create_task(observability_svc.record_event({
        "timestamp": datetime.utcnow().isoformat(),
        "query_category": category,
        "model_used": result.get("model", "n/a"),
        "cache_hit": False,
        "cache_type": None,
        "timings_ms": timings,
        "hallucination_confidence": hallucination_check["confidence"],
        "estimated_cost_usd": estimate_cost(
            result.get("model", ""),
            input_tokens=len(clean_query) // 4,
            output_tokens=len(result.get("answer", "")) // 4,
        ),
        "retrieval_broadened": retrieval_broadened,
    }, user_uid))

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

    messages = await firestore_svc.get_messages(
        token["uid"], session_id, limit
    )
    return {
        "session": session,
        "messages": messages,
        "count": len(messages),
    }


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
        raise HTTPException(
            status_code=400, detail="Title too long (max 100 chars)"
        )

    await firestore_svc.update_session_title(
        token["uid"], session_id, title
    )
    return {"updated": True, "session_id": session_id, "title": title}