# Architecture Documentation — AI-Powered Study Buddy

## Overview

This document describes the technical architecture of the AI-Powered Study Buddy, a full-stack application consisting of a FastAPI backend, a vanilla JavaScript frontend, and a MySQL database, all containerized with Docker.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                                       │
│                                                                                │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐ │
│  │ index.html  │  │ dashboard.html│  │  tutor.html   │  │  flashcards.html │ │
│  │ (Landing)   │  │ (Dashboard)  │  │  (AI Tutor)   │  │  (Study)         │ │
│  └─────────────┘  └──────────────┘  └───────────────┘  └──────────────────┘ │
│                                                                                │
│       assets/js/api.js ──── assets/js/auth.js                                │
│       assets/js/ui.js  ──── assets/js/utils.js                               │
│       assets/css/styles.css (Tailwind + custom CSS)                           │
│                                                                                │
│  Authentication: Clerk JS SDK                                                  │
│  Communication: fetch() + EventSource (SSE for streaming)                     │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                 │ HTTPS (REST + SSE)
                                 │ Authorization: Bearer <Clerk JWT>
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            API LAYER (FastAPI)                                │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                       app/main.py                                    │    │
│  │  CORS Middleware │ Request Logging │ Rate Limiting (slowapi)          │    │
│  │  Exception Handlers │ Health Check │ Router Includes                  │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ │
│  │  /auth   │ │  /users  │ │/documents│ │/tutor  │ │/summary│ │ /quizzes │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ └────────┘ └──────────┘ │
│  ┌──────────┐ ┌────────────────────┐ ┌───────────────────────────────────┐  │
│  │/flashcard│ │    /learning       │ │         /analytics                │  │
│  └──────────┘ └────────────────────┘ └───────────────────────────────────┘  │
│                                                                                │
│  Security Layer:                                                               │
│    core/security.py → verify_clerk_token() → JWKS endpoint                   │
│    core/exceptions.py → standardised {success, error} responses               │
│    api/deps.py → get_current_user() dependency                                │
└─────────────────────────────┬────────────────────────────────────────────────┘
                               │
              ┌────────────────┴─────────────────┐
              │                                   │
              ▼                                   ▼
┌─────────────────────────┐       ┌───────────────────────────────────┐
│     DATA LAYER           │       │      AI LAYER                     │
│                          │       │                                   │
│  SQLAlchemy async engine │       │  OpenAI SDK (async)               │
│  aiomysql driver         │       │  LLM_BASE_URL configurable        │
│  Alembic migrations      │       │                                   │
│                          │       │  Prompts:                         │
│  MySQL 8.0               │       │  - tutor.txt (6 modes)            │
│  ┌────────────────────┐  │       │  - summarization.txt              │
│  │ users              │  │       │  - flashcards.txt                 │
│  │ documents          │  │       │  - quiz_generation.txt            │
│  │ topics             │  │       │  - recommendations.txt            │
│  │ summaries          │  │       │                                   │
│  │ flashcards         │  │       │  Streaming: async generator       │
│  │ quizzes            │  │       │  → SSE text/event-stream          │
│  │ quiz_questions     │  │       └───────────────────────────────────┘
│  │ quiz_attempts      │  │
│  │ quiz_answers       │  │
│  │ learning_progress  │  │
│  │ study_sessions     │  │
│  └────────────────────┘  │
└─────────────────────────-┘
```

---

## Request Flow Diagrams

### Standard API Request

```
Browser                    FastAPI                     MySQL
  │                           │                          │
  │── GET /api/documents ──►  │                          │
  │   Bearer: <token>         │                          │
  │                           │── verify_clerk_token() ─►│
  │                           │   (JWKS cache hit)        │
  │                           │                          │
  │                           │── get_current_user() ───►│
  │                           │◄─ User record ──────────│
  │                           │                          │
  │                           │── SELECT documents ─────►│
  │                           │◄─ [Document, ...] ──────│
  │                           │                          │
  │◄─ 200 {success, data} ──  │                          │
```

### AI Tutor Streaming Request

```
Browser                    FastAPI                     OpenAI
  │                           │                          │
  │── POST /api/tutor/chat ─► │                          │
  │   {message, mode, ...}    │── verify + auth ─────────│
  │                           │                          │
  │                           │── chat.completions ─────►│
  │                           │   (stream=True)           │
  │                           │◄─ AsyncStream ───────────│
  │◄─ text/event-stream ──── │                          │
  │   data: chunk1\n\n        │◄─ chunk1                 │
  │   data: chunk2\n\n        │◄─ chunk2                 │
  │   data: [DONE]\n\n        │◄─ [DONE]                 │
```

### Document Upload Flow

```
Browser           FastAPI            Storage         MySQL
  │                  │                  │               │
  │── POST /docs ──► │                  │               │
  │   multipart      │── validate ─────►│               │
  │                  │── write file ───►│               │
  │                  │◄─ path ──────────│               │
  │                  │── INSERT doc ───────────────────►│
  │◄─ 201 {doc} ──  │◄─ doc ───────────────────────────│
```

---

## Key Design Decisions

### 1. Async-First Architecture
All database operations use `SQLAlchemy[asyncio]` with `aiomysql`. This allows FastAPI to handle thousands of concurrent connections without blocking on I/O.

### 2. Clerk for Authentication
Rather than building custom JWT auth, we delegate identity to Clerk. The backend:
1. Fetches the JWKS from Clerk's well-known endpoint
2. Caches keys in memory
3. Verifies each request's Bearer token locally (no round-trip to Clerk per request)

### 3. SSE for LLM Streaming
The tutor chat uses Server-Sent Events (SSE) rather than WebSockets. SSE is:
- Simpler (unidirectional — server → client)
- Automatically reconnectable
- Works through most proxies and CDNs
- Sufficient for streaming text chunks

### 4. SM-2 Spaced Repetition
Flashcard scheduling implements the SM-2 algorithm:
- Quality ratings 0–5 determine the next review interval
- Ease factor (EF) adjusts based on performance history
- Cards due for review are surfaced first in study sessions

### 5. Standardised Error Format
All API errors return:
```json
{
  "success": false,
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Human readable explanation"
  }
}
```
This allows the frontend API client to handle all errors uniformly.

### 6. LLM Provider Agnosticism
The backend uses the OpenAI SDK with a configurable `LLM_BASE_URL`. This allows swapping to:
- Together AI, Groq, Anyscale (cheaper/faster)
- Ollama (local models for privacy)
- Azure OpenAI (enterprise)
- Any other OpenAI-compatible API

---

## Data Models

### User ↔ Document relationship
```
User (1) ──── (many) Document
     ├────── (many) Summary (via document)
     ├────── (many) Quiz (via document)
     ├────── (many) Flashcard (via document)
     ├────── (many) LearningProgress (via topic)
     └────── (many) StudySession
```

### Quiz structure
```
Quiz (1) ──── (many) QuizQuestion
              └──── (many) QuizAnswer
Quiz (1) ──── (many) QuizAttempt
              └──── (many) QuizAnswer
```

---

## Security Model

| Layer | Mechanism |
|---|---|
| Auth | Clerk JWT, verified via JWKS (RS256) |
| Authorization | Owner check: `document.user_id == current_user.id` |
| Rate Limiting | slowapi: `RATE_LIMIT_PER_MINUTE` per IP |
| File Upload | MIME type allowlist + size limit |
| SQL Injection | SQLAlchemy ORM (parameterised queries) |
| XSS (frontend) | `escapeHtml()` in ui.js before DOM insertion |
| CORS | Configured allowlist via `CORS_ORIGINS` env var |

---

## Configuration Reference

All configuration lives in [`backend/app/core/config.py`](../backend/app/core/config.py) as a Pydantic `BaseSettings` class that reads from environment variables or a `.env` file.

Key derived properties:
- `settings.is_production` — `True` when `APP_ENV == "production"`
- `settings.max_file_size_bytes` — `MAX_FILE_SIZE_MB * 1024 * 1024`
- `settings.clerk_jwks_url` — decoded from `CLERK_PUBLISHABLE_KEY`

---

## Phase Roadmap

| Phase | Status | Content |
|---|---|---|
| **Phase 1** | ✅ Complete | Foundation: project structure, models, API routes, and frontend shell |
| **Phase 2** | ✅ Complete | Document processing pipeline: PDF/DOCX/TXT/Markdown extraction and background processing |
| **Phase 3** | 🔜 Planned | Conversation history persistence and automatic topic tagging; recommendations currently use deterministic weak-topic rules |
| **Phase 4** | 🔜 Planned | Advanced analytics charts, study streak gamification, export features |
