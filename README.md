# JustiBot — Indian Legal Assistant Chatbot

**JustiBot** is a RAG-powered chatbot that helps Indian citizens understand their legal rights, acts, and procedures. It uses a local embedding pipeline, Qdrant Cloud for vector search, Groq for LLM inference, and Firebase for authentication.

---

## Repository Structure

```
justibot/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Pydantic-settings config
│   ├── middleware/
│   │   ├── auth.py              # Firebase JWT verification
│   │   ├── rate_limit.py        # Per-user slowapi rate limiting
│   │   └── security.py          # Input sanitization + injection detection
│   ├── routers/
│   │   ├── health.py            # Health check endpoints
│   │   └── chat.py              # Chat endpoints (stub — Phase 2 adds RAG)
│   ├── services/
│   │   ├── qdrant_service.py    # Qdrant client wrapper
│   │   ├── groq_service.py      # Groq LLM wrapper (stub)
│   │   └── redis_service.py     # Upstash Redis cache wrapper
│   ├── corpus/
│   │   ├── ingest.py            # One-time ingestion script
│   │   ├── chunker.py           # Document chunking (PDF + HTML)
│   │   ├── embedder.py          # Local sentence-transformers embeddings
│   │   └── sources.py           # Legal source URLs and helpline data
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── README.md
└── .gitignore
```

---

## Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Corpus ingestion pipeline | ✅ Complete |
| 1 | FastAPI backend foundation | ✅ Complete |
| 2 | RAG pipeline (Groq + Qdrant) | 🔜 Planned |
| 3 | Session storage (Firestore) | 🔜 Planned |
| 4+ | Frontend | 🔜 Planned |

---

## Phase 0 — Corpus Ingestion (One-time)

### Prerequisites

1. Python 3.11+
2. A Qdrant Cloud cluster (free tier works)
3. A `.env` file in `backend/` — copy from `.env.example`

### Setup

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Run ingestion

```bash
# From the project root (not inside backend/)
python -m backend.corpus.ingest
```

This will:
1. Download 6 Indian legal PDFs + 1 HTML page
2. Chunk documents into ~800-char overlapping segments
3. Embed each chunk using `all-MiniLM-L6-v2` (384 dims, runs locally)
4. Upload all vectors to Qdrant Cloud (`justibot_legal` collection)
5. Upload 6 helpline entries as additional searchable chunks

Estimated time: 15–30 minutes depending on download speeds.

### Legal Sources Ingested

| Act | Category | Year |
|-----|----------|------|
| Bharatiya Nyaya Sanhita (BNS) | Criminal | 2023 |
| Bharatiya Nagarik Suraksha Sanhita (BNSS) | Procedural | 2023 |
| Constitution of India | Constitutional | 2023 |
| RTI Act | Civil | 2005 |
| Consumer Protection Act | Consumer | 2019 |
| Information Technology Act | Cyber | 2000 |
| Cybercrime.gov.in Portal | Cyber | 2024 |

---

## Phase 1 — FastAPI Backend

### Running locally

```bash
# From the project root
uvicorn backend.main:app --reload
```

API docs available at: http://localhost:8000/docs

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Root ping |
| GET | `/api/health` | No | Liveness check |
| GET | `/api/health/detailed` | Firebase | Connectivity check |
| POST | `/api/chat` | Firebase | Legal query (stub) |
| GET | `/api/chat/sessions` | Firebase | List sessions (stub) |
| DELETE | `/api/chat/sessions/{id}` | Firebase | Delete session (stub) |

### Authentication

All `/api/chat` endpoints require:
```
Authorization: Bearer <Firebase ID Token>
```

### Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in your credentials:

```bash
cp backend/.env.example backend/.env
```

Required:
- `QDRANT_URL` + `QDRANT_API_KEY` — from [Qdrant Cloud](https://cloud.qdrant.io)
- `GROQ_API_KEY` — from [GroqCloud](https://console.groq.com)
- `UPSTASH_REDIS_URL` + `UPSTASH_REDIS_TOKEN` — from [Upstash](https://upstash.com)
- `FIREBASE_PROJECT_ID` + `FIREBASE_SERVICE_ACCOUNT_JSON` — from Firebase Console

---

## Docker

```bash
docker build -t justibot-backend ./backend
docker run -p 8000:8000 --env-file ./backend/.env justibot-backend
```

---

## Security

- Firebase JWT verification on all protected endpoints
- Per-user rate limiting (20 requests/minute default)
- Input sanitization: strips control characters, truncates at 2000 chars
- Prompt injection detection: blocks 11 known adversarial patterns
- No credentials in source code — all secrets via environment variables

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| API | FastAPI + uvicorn |
| Auth | Firebase Admin SDK |
| Vector DB | Qdrant Cloud |
| Embeddings | sentence-transformers (local) |
| LLM | Groq (llama-3.1-70b-versatile) |
| Cache | Upstash Redis |
| Rate limiting | slowapi |
