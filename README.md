# 🎓 AI-Powered Study Buddy

<div align="center">

**An intelligent, full-stack learning assistant powered by AI.**  
Upload your study materials. Get smart summaries. Generate quizzes and flashcards. Chat with an AI tutor. Track your progress.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://mysql.com)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-CSS-38B2AC?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Clerk](https://img.shields.io/badge/Auth-Clerk-6C47FF?logo=clerk&logoColor=white)](https://clerk.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Running Locally (Docker)](#running-locally-docker)
- [Running Without Docker](#running-without-docker)
- [Database Migrations](#database-migrations)
- [Clerk Setup](#clerk-setup)
- [LLM Provider Setup](#llm-provider-setup)
- [Frontend Setup](#frontend-setup)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

Study Buddy is a complete, production-quality AI-powered learning platform. Students upload their PDF notes, textbooks, or markdown files — the app automatically extracts the text, then uses AI to generate summaries, quizzes, and flashcards from that content. An AI tutor chat lets students ask any question, with optional document context.

The system tracks quiz performance per topic, calculates mastery scores using a weighted average algorithm, and surfaces personalized recommendations. Flashcard reviews use the SM-2 spaced repetition algorithm to schedule cards optimally.

---

## Features

| Feature | Description |
|---|---|
| 🤖 **AI Tutor** | Streaming chat with 6 modes: Explain, Deep Dive, Quiz Me, Socratic, Exam Prep, Summarize |
| 📄 **Document Upload** | PDF, DOCX, TXT, Markdown — auto text extraction in the background |
| 📋 **AI Summarization** | 5 summary types: Quick, Detailed, Bullet Points, Exam Revision, Simple Explanation |
| 🃏 **Smart Flashcards** | AI-generated cards + SM-2 spaced repetition scheduling |
| 📝 **Quiz Generator** | Multiple-choice quizzes with explanations — easy/medium/hard/mixed difficulty |
| 📊 **Learning Analytics** | Mastery scores, study streak, topic performance, recent activity |
| 🎯 **Personalization** | Weak-topic detection, automated study recommendations |
| 🌙 **Dark Mode** | Full dark/light theme with persistence |
| 🔐 **Secure Auth** | Clerk JWT authentication — every resource is user-isolated |

---

## Tech Stack

### Backend
- **Python 3.12+** / **FastAPI 0.115+** — async API framework
- **SQLAlchemy 2.x** (async) + **aiomysql** — ORM with async MySQL driver
- **Alembic** — database schema migrations
- **Pydantic v2** — request/response validation and settings
- **python-jose** — Clerk JWT verification via JWKS
- **pypdf** + **python-docx** — PDF and DOCX text extraction
- **OpenAI SDK** — LLM integration (streaming + JSON mode)
- **SlowAPI** — rate limiting

### Frontend
- **HTML5** + **Tailwind CSS** (CDN) — no build step required
- **Vanilla JavaScript ES6** modules — `api.js`, `auth.js`, `ui.js`, etc.
- **Clerk JS SDK** — authentication widget and JWT tokens
- **Server-Sent Events** — real-time AI tutor streaming

### Infrastructure
- **MySQL 8.0** — relational database
- **Docker Compose** — one-command local development
- **Uvicorn** — ASGI server

---

## Architecture

```
Browser (HTML + JS)
       │
       │  REST + SSE (port 8000)
       ▼
┌─────────────────────────────────────────────────┐
│              FastAPI Application                 │
│                                                 │
│  ┌──────────┐  ┌───────────────────────────┐   │
│  │   CORS   │  │   Clerk JWT Middleware     │   │
│  └──────────┘  └───────────────────────────┘   │
│                                                 │
│  /api/auth      /api/documents   /api/tutor     │
│  /api/quizzes   /api/flashcards  /api/summaries │
│  /api/learning  /api/analytics   /api/users     │
│                                                 │
│  ┌────────────────────────────────────────────┐ │
│  │              Service Layer                 │ │
│  │  document_service  learning_service        │ │
│  │  session_service   (quiz/flash in routes)  │ │
│  └────────────────────────────────────────────┘ │
│                                                 │
│  ┌──────────────┐   ┌───────────────────────┐  │
│  │  SQLAlchemy  │   │    OpenAI / LLM API   │  │
│  │  (async)     │   │    (streaming + JSON) │  │
│  └──────┬───────┘   └───────────────────────┘  │
└─────────│───────────────────────────────────────┘
          │
    ┌─────▼──────┐
    │  MySQL 8   │
    │ (10 tables)│
    └────────────┘
```

### Authentication Flow

```
1. User signs up/in via Clerk widget (frontend)
2. Clerk issues a signed JWT (RS256)
3. Frontend sends: Authorization: Bearer <JWT>
4. Backend fetches Clerk JWKS → verifies JWT signature
5. Extracts clerk_user_id from sub claim
6. Looks up (or creates) local User record in MySQL
7. All DB resources are scoped to that user_id
```

### Document Processing Flow

```
Upload file → Validate MIME + size → Save to disk (UUID filename)
     → Write DB record (status: "uploaded")
     → FastAPI BackgroundTask triggers
     → pypdf / python-docx extracts text
     → Update DB record (status: "ready", extracted_text)
     → Frontend polls every 3s until "ready"
```

---

## Prerequisites

- **Docker Desktop** 4.x+ (includes Docker Compose v2)
- **Git**
- A **Clerk** account (free) — [clerk.com](https://clerk.com)
- An **OpenAI API key** (or compatible provider)
- A text editor or **VS Code** with Live Server extension (for the frontend)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/nitinsmali/AI-Powered-Study-Buddy.git
cd AI-Powered-Study-Buddy

# 2. Copy and fill in environment variables
cp .env.example .env
# Edit .env — add your CLERK_SECRET_KEY, CLERK_PUBLISHABLE_KEY, LLM_API_KEY

# 3. Start backend + database
docker compose up --build

# 4. Run database migrations (in a new terminal)
docker exec -it ai-powered-study-buddy-backend-1 alembic upgrade head

# 5. Open the frontend
# Option A: VS Code → right-click frontend/index.html → "Open with Live Server"
# Option B: python -m http.server 5500 (run inside /frontend)
# Option C: open frontend/index.html directly in your browser
```

That's it. Go to `http://127.0.0.1:5500/frontend/index.html`, click **Get Started**, sign up, and start studying.

---

## Environment Variables

Copy `.env.example` to `.env` and set these values:

```env
# ── Required ──────────────────────────────────────────────────────────────────

# MySQL credentials (used by both Docker and the backend)
DATABASE_URL=mysql+aiomysql://study_user:study_pass@db:3306/study_buddy
MYSQL_ROOT_PASSWORD=changeme_root
MYSQL_DATABASE=study_buddy
MYSQL_USER=study_user
MYSQL_PASSWORD=study_pass

# Clerk — get from https://dashboard.clerk.com → your app → API Keys
CLERK_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxx
CLERK_SECRET_KEY=sk_test_xxxxxxxxxxxx

# LLM provider API key
LLM_API_KEY=sk-xxxxxxxxxxxx

# ── Optional ──────────────────────────────────────────────────────────────────

# LLM model (default: gpt-4o-mini)
LLM_MODEL=gpt-4o-mini

# Override for non-OpenAI providers (Groq, Together, Ollama — see below)
LLM_BASE_URL=

# Uploaded file storage path inside the container
STORAGE_PATH=./uploads

# Max upload size in MB
MAX_FILE_SIZE_MB=50

# Comma-separated allowed CORS origins
CORS_ORIGINS=http://localhost:3000,http://localhost:5500,http://127.0.0.1:5500

# Rate limit per IP per minute
RATE_LIMIT_PER_MINUTE=60

# Environment: development | production
APP_ENV=development

# Log level: DEBUG | INFO | WARNING | ERROR
LOG_LEVEL=INFO
```

---

## Running Locally (Docker)

### Start everything

```bash
docker compose up --build
```

Services started:
| Service | URL | Notes |
|---|---|---|
| FastAPI backend | `http://localhost:8000` | Auto-reloads on code changes |
| Swagger UI (API docs) | `http://localhost:8000/docs` | Available in development |
| MySQL | `localhost:3307` | Port 3307 to avoid conflicts |
| Health check | `http://localhost:8000/health` | Returns `{"status":"healthy"}` |

### Run migrations (first time only)

```bash
docker exec -it ai-powered-study-buddy-backend-1 alembic upgrade head
```

### Stop everything

```bash
docker compose down
# To also remove database data:
docker compose down -v
```

### View logs

```bash
docker logs -f ai-powered-study-buddy-backend-1
docker logs -f ai-powered-study-buddy-db-1
```

---

## Running Without Docker

If you prefer to run the backend directly:

```bash
# 1. Install Python 3.12+
# 2. Create a virtual environment
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set DATABASE_URL to point to your local MySQL
# Edit .env → DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/study_buddy

# 5. Run the backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Database Migrations

This project uses **Alembic** for schema management.

```bash
# Apply all pending migrations (run after first docker compose up)
docker exec -it ai-powered-study-buddy-backend-1 alembic upgrade head

# Check current migration version
docker exec -it ai-powered-study-buddy-backend-1 alembic current

# Create a new migration after model changes
docker exec -it ai-powered-study-buddy-backend-1 alembic revision --autogenerate -m "add new field"

# Roll back one step
docker exec -it ai-powered-study-buddy-backend-1 alembic downgrade -1
```

### Database schema (10 tables)

```
users              — Clerk-synced user accounts
documents          — Uploaded study materials (with extracted_text)
summaries          — AI-generated document summaries
topics             — User/document topics for progress tracking
quizzes            — Generated quizzes
quiz_questions     — Individual MCQ questions (options stored as JSON)
quiz_attempts      — User quiz submissions with scores
quiz_answers       — Individual answer records
flashcards         — AI-generated flashcards with SM-2 fields
learning_progress  — Per-topic mastery scores and answer stats
study_sessions     — Activity log (tutor chats, quizzes, reviews)
```

---

## Clerk Setup

1. Go to [clerk.com](https://clerk.com) → Create a free account
2. Click **"Create application"** → name it "Study Buddy"
3. Choose sign-in options (Email + Password recommended; Google optional)
4. Navigate to **Configure → API Keys**
5. Copy:
   - **Publishable key** → `pk_test_...` → goes in `.env` AND all HTML `<meta>` tags
   - **Secret key** → `sk_test_...` → goes in `.env` only (never in frontend)

> **Important:** In every HTML file there is a meta tag:
> ```html
> <meta name="clerk-publishable-key" content="pk_test_YOUR_KEY">
> ```
> This is how the frontend JavaScript loads the Clerk widget.

---

## LLM Provider Setup

The backend uses an OpenAI-compatible API. Set `LLM_API_KEY` and optionally `LLM_BASE_URL` + `LLM_MODEL`.

### OpenAI (default)
```env
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=
```

### Groq (free tier, very fast)
```env
LLM_API_KEY=gsk_...
LLM_MODEL=llama-3.1-70b-versatile
LLM_BASE_URL=https://api.groq.com/openai/v1
```
Get key at: [console.groq.com](https://console.groq.com)

### Together AI (free $25 credit)
```env
LLM_API_KEY=...
LLM_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo
LLM_BASE_URL=https://api.together.xyz/v1
```
Get key at: [api.together.xyz](https://api.together.xyz)

### Ollama (local, free)
```env
LLM_API_KEY=ollama
LLM_MODEL=llama3.2
LLM_BASE_URL=http://host.docker.internal:11434/v1
```
Install Ollama at: [ollama.com](https://ollama.com) → `ollama pull llama3.2`

---

## Frontend Setup

The frontend is plain HTML + JavaScript — **no build step, no npm**.

### Serve the frontend

```bash
# Option 1: VS Code Live Server (recommended)
# Install "Live Server" extension → right-click index.html → "Open with Live Server"
# Opens at: http://127.0.0.1:5500/frontend/index.html

# Option 2: Python built-in server
cd frontend && python -m http.server 5500
# Opens at: http://localhost:5500

# Option 3: Open directly (file://)
# Simply double-click frontend/index.html
```

### CORS note
If you open with VS Code Live Server (port 5500), the default CORS origins already include `http://127.0.0.1:5500`.  
If you use a different port, add it to `CORS_ORIGINS` in your `.env` and restart Docker.

---

## API Reference

Full interactive documentation: **`http://localhost:8000/docs`**

### Auth
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/sync` | Create/return user record from Clerk ID |
| `POST` | `/api/auth/sync/profile` | Upsert user profile (email, name, avatar) |

### Users
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/users/me` | Get current user profile |
| `PUT` | `/api/users/me` | Update profile (name, avatar) |

### Documents
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/documents` | Upload a document (multipart/form-data) |
| `GET` | `/api/documents` | List all user documents |
| `GET` | `/api/documents/{id}` | Get single document |
| `DELETE` | `/api/documents/{id}` | Delete document + file |

### AI Tutor
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/tutor/chat` | Stream AI tutor response (SSE) |

### Summaries
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/summaries` | Generate a summary from a document |
| `GET` | `/api/summaries` | List summaries (filter by `document_id`) |
| `GET` | `/api/summaries/{id}` | Get single summary |
| `DELETE` | `/api/summaries/{id}` | Delete summary |

### Quizzes
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/quizzes/generate` | Generate a quiz from a document |
| `GET` | `/api/quizzes` | List all user quizzes |
| `GET` | `/api/quizzes/{id}` | Get quiz with questions |
| `POST` | `/api/quizzes/{id}/attempt` | Submit quiz answers → get score |
| `DELETE` | `/api/quizzes/{id}` | Delete quiz |

### Flashcards
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/flashcards/generate` | Generate flashcards from a document |
| `GET` | `/api/flashcards` | List flashcards (supports `due_only=true`) |
| `POST` | `/api/flashcards/{id}/review` | Record SM-2 review (quality 0–5) |
| `DELETE` | `/api/flashcards/{id}` | Delete flashcard |

### Learning & Analytics
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/learning/progress` | Topic mastery scores |
| `GET` | `/api/learning/recommendations` | Personalized study suggestions |
| `GET` | `/api/analytics/summary` | Full dashboard stats |

---

## Project Structure

```
AI-Powered-Study-Buddy/
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, middleware, routers
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic settings (env vars)
│   │   │   ├── security.py          # Clerk JWT verification
│   │   │   ├── exceptions.py        # Custom exceptions + handlers
│   │   │   └── logging.py           # Structured logging
│   │   ├── api/
│   │   │   ├── deps.py              # Shared FastAPI dependencies
│   │   │   └── routes/              # One file per feature
│   │   ├── models/                  # SQLAlchemy ORM models (10 tables)
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── services/                # Business logic services
│   │   │   ├── document_service.py  # Background text extraction
│   │   │   ├── learning_service.py  # Mastery score calculation
│   │   │   └── session_service.py   # Study session logging
│   │   ├── utils/
│   │   │   ├── pdf_parser.py        # PDF/DOCX/TXT text extraction
│   │   │   └── validators.py        # File validation helpers
│   │   ├── db/
│   │   │   ├── session.py           # Async SQLAlchemy engine + session
│   │   │   └── base.py              # Declarative base + model imports
│   │   └── prompts/                 # AI system prompts (external .txt files)
│   ├── alembic/                     # Database migration scripts
│   ├── Dockerfile                   # Multi-stage Python 3.12 image
│   └── requirements.txt
│
├── frontend/
│   ├── index.html                   # Landing page
│   ├── dashboard.html               # Main dashboard
│   ├── tutor.html                   # AI tutor chat
│   ├── documents.html               # Upload & manage documents
│   ├── document.html                # Single document actions
│   ├── flashcards.html              # Flashcard study mode
│   ├── quizzes.html                 # Quiz generation & taking
│   ├── analytics.html               # Learning analytics
│   ├── settings.html                # Profile & preferences
│   ├── auth/
│   │   └── signin.html              # Clerk sign-in widget
│   └── assets/
│       ├── css/styles.css           # Custom CSS (animations, components)
│       └── js/
│           ├── api.js               # Centralized API client + SSE
│           ├── auth.js              # Clerk SDK wrapper
│           ├── ui.js                # Toast, skeleton, empty state
│           ├── utils.js             # Markdown renderer, formatters
│           ├── dashboard.js         # Dashboard logic
│           ├── tutor.js             # Tutor chat logic
│           ├── documents.js         # Upload + document list
│           ├── flashcards.js        # Flashcard review + SM-2
│           ├── quizzes.js           # Quiz taking + results
│           ├── analytics.js         # Analytics page
│           └── settings.js          # Settings page
│
├── tests/                           # Pytest test suite (73 tests)
│   ├── test_document_processing.py
│   ├── test_quiz_scoring.py
│   ├── test_security.py
│   └── test_validators.py
│
├── scripts/
│   └── init.sql                     # MySQL charset initialization
│
├── docs/
│   └── architecture.md              # Detailed architecture docs
│
├── docker-compose.yml               # Backend + MySQL services
├── .env.example                     # Environment variable template
├── pytest.ini                       # Test configuration
└── README.md
```

---

## Testing

```bash
# Run all tests (from project root)
cd backend
python -m pytest ../tests/ -v

# Run a specific test file
python -m pytest ../tests/test_quiz_scoring.py -v

# Run with coverage (requires pytest-cov)
python -m pytest ../tests/ --cov=app --cov-report=term-missing
```

**Test coverage:**
| Test file | Tests | What's covered |
|---|---|---|
| `test_quiz_scoring.py` | 25 | Quiz scoring, SM-2 algorithm, mastery calculation |
| `test_document_processing.py` | 13 | Text extraction, clean text, MIME dispatch |
| `test_security.py` | 14 | Auth guards, ownership logic, file security |
| `test_validators.py` | 21 | Extension validation, MIME check, filename sanitisation |

---

## Troubleshooting

### Backend won't start — `CORS_ORIGINS` parse error
This happens if `CORS_ORIGINS` in `.env` is empty or malformed.  
**Fix:** Ensure `.env` has `CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500` (no spaces around commas).

### Backend unhealthy in Docker
```bash
# Check what went wrong
docker logs ai-powered-study-buddy-backend-1 --tail 50

# Restart after fixing the issue
docker compose restart backend
```

### Clerk widget doesn't appear on sign-in page
- The `<meta name="clerk-publishable-key" content="pk_test_...">` tag must have your real publishable key.
- Check browser console for errors — a wrong key shows `ClerkJS error: Invalid publishable key`.

### `User account not found` on API calls
- The user must call `POST /api/auth/sync/profile` after first sign-in.
- This happens automatically on sign-in. If it failed, sign out and sign in again.

### Document stuck at "Processing"
```bash
# Check backend logs for extraction errors
docker logs ai-powered-study-buddy-backend-1 | grep -i "process_document"

# Manually check document status
curl -H "Authorization: Bearer <your-token>" http://localhost:8000/api/documents
```

### MySQL connection refused
```bash
# Check if db container is healthy
docker ps

# Wait for MySQL to be fully ready (can take 30-60 seconds on first start)
docker logs ai-powered-study-buddy-db-1 --tail 20
```

### Alembic — `Table already exists`
```bash
# Reset and reapply
docker exec -it ai-powered-study-buddy-backend-1 alembic downgrade base
docker exec -it ai-powered-study-buddy-backend-1 alembic upgrade head
```

### CORS errors in browser
Add your Live Server origin to `.env`:
```env
CORS_ORIGINS=http://localhost:3000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:YOUR_PORT
```
Then restart: `docker compose restart backend`

---

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feat/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to the branch: `git push origin feat/your-feature`
5. Open a Pull Request

### Commit message format
```
feat: add new feature
fix: resolve bug
docs: update documentation
refactor: improve code structure
test: add or update tests
chore: maintenance tasks
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
Built with ❤️ using FastAPI, Tailwind CSS, and OpenAI
</div>

