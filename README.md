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
[![Tests](https://img.shields.io/badge/Tests-73%20passing-brightgreen)](./tests)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [⚡ Startup Cheatsheet](#-startup-cheatsheet)
- [Quick Start (First Time)](#quick-start-first-time)
- [🌐 Useful URLs While Running](#-useful-urls-while-running)
- [🚀 Complete First-Use Flow](#-complete-first-use-flow)
- [📂 Opening the App](#-opening-the-app)
- [Environment Variables](#environment-variables)
- [Running Locally (Docker)](#running-locally-docker)
- [Running Without Docker](#running-without-docker)
- [Database Migrations](#database-migrations)
- [Clerk Setup](#clerk-setup)
- [LLM Provider Setup](#llm-provider-setup)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

Study Buddy is a complete, production-quality AI-powered learning platform. Students upload their PDF notes, textbooks, or markdown files — the app automatically extracts the text, then uses AI to generate summaries, quizzes, and flashcards from that content. An AI tutor chat lets students ask any question, with optional document context injected automatically.

The system tracks quiz performance per topic, calculates mastery scores using a weighted average algorithm, and surfaces personalized study recommendations. Flashcard reviews use the **SM-2 spaced repetition algorithm** to schedule cards optimally.

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
       │  REST + SSE  (port 8000)
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
3. Frontend sends:  Authorization: Bearer <JWT>
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
     → Frontend polls every 3 s until "ready"
```

---

## Prerequisites

Before you start, make sure you have:

- **Docker Desktop** 4.x+ (includes Docker Compose v2) — [download](https://www.docker.com/products/docker-desktop/)
- **Git** — [download](https://git-scm.com/downloads)
- A **Clerk** account (free) — [clerk.com](https://clerk.com)
- An **LLM API key** — OpenAI, Groq (free), Together AI, or local Ollama
- **VS Code** with the [Live Server](https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer) extension *(recommended for the frontend)*

---

## ⚡ Startup Cheatsheet

> Copy-paste these commands every time you want to run the project.

### Every time you start

```bash
# Terminal 1 — start backend + database
docker compose up
```

```bash
# Open the app (pick one)
# VS Code → right-click frontend/index.html → "Open with Live Server"
# OR:
cd frontend && python -m http.server 5500
```

### First time only (after `docker compose up` is running)

```bash
# Terminal 2 — create all database tables (run once, ever)
docker exec -it ai-poweredstudybuddy-backend-1 alembic upgrade head
```

### Stop everything

```bash
docker compose down
```

### Rebuild after code changes

```bash
docker compose up --build
```

### Restart just the backend (e.g. after editing `.env`)

```bash
docker compose restart backend
```

### View live backend logs

```bash
docker logs -f ai-poweredstudybuddy-backend-1
```

### Check container health

```bash
docker ps
```

---

## Quick Start (First Time)

```bash
# 1. Clone the repository
git clone https://github.com/nitinsmali/AI-Powered-Study-Buddy.git
cd AI-Powered-Study-Buddy

# 2. Create your .env file
cp .env.example .env
# Open .env and fill in:
#   CLERK_SECRET_KEY=sk_test_...       ← from clerk.com → API Keys
#   CLERK_PUBLISHABLE_KEY=pk_test_...  ← from clerk.com → API Keys
#   LLM_API_KEY=sk-...                 ← from openai.com (or Groq/Together)

# 3. Start backend + database
docker compose up --build

# 4. (New terminal) Run database migrations — FIRST TIME ONLY
docker exec -it ai-poweredstudybuddy-backend-1 alembic upgrade head

# 5. Open the frontend
# → VS Code: right-click frontend/index.html → "Open with Live Server"
# → Or: cd frontend && python -m http.server 5500
```

That's it. Visit **`http://127.0.0.1:5500/frontend/index.html`**, click **Get Started**, and you're in.

---

## 🌐 Useful URLs While Running

| What | URL | Notes |
|---|---|---|
| **The App** | `http://127.0.0.1:5500/frontend/index.html` | Via VS Code Live Server |
| **The App** | `http://localhost:5500` | Via Python http.server |
| **Health Check** | `http://localhost:8000/health` | Returns `{"status":"healthy"}` |
| **API Docs (Swagger)** | `http://localhost:8000/docs` | Interactive — try any endpoint live |
| **API Docs (ReDoc)** | `http://localhost:8000/redoc` | Clean read-only reference |
| **MySQL** | `localhost:3307` | Port 3307 (not 3306) to avoid conflicts |
| **Sign In page** | `http://127.0.0.1:5500/frontend/auth/signin.html` | Direct link |
| **Dashboard** | `http://127.0.0.1:5500/frontend/dashboard.html` | Requires sign-in |
| **AI Tutor** | `http://127.0.0.1:5500/frontend/tutor.html` | Streaming chat |
| **Documents** | `http://127.0.0.1:5500/frontend/documents.html` | Upload & manage |
| **Flashcards** | `http://127.0.0.1:5500/frontend/flashcards.html` | SM-2 review mode |
| **Quizzes** | `http://127.0.0.1:5500/frontend/quizzes.html` | Generate & take quizzes |
| **Analytics** | `http://127.0.0.1:5500/frontend/analytics.html` | Progress charts |
| **Settings** | `http://127.0.0.1:5500/frontend/settings.html` | Profile & theme |

> **Tip:** Bookmark `http://localhost:8000/docs` — it lets you test every API endpoint directly in the browser without needing a frontend.

---

## 🚀 Complete First-Use Flow

Follow these steps in order on your very first run:

```
STEP 1 ── Start Docker
          docker compose up --build
          Wait until you see:
          "Application startup complete."
          "Database connection established."

STEP 2 ── Run migrations (new terminal, first time only)
          docker exec -it ai-poweredstudybuddy-backend-1 alembic upgrade head
          Expected: "Running upgrade -> 001, Initial migration"

STEP 3 ── Open the app
          VS Code → right-click frontend/index.html → Open with Live Server
          Opens at: http://127.0.0.1:5500/frontend/index.html

STEP 4 ── Landing page loads
          You see the Study Buddy hero page
          Click "Get Started Free" or "Sign In"

STEP 5 ── Sign up with Clerk
          Enter your email + password (or use Google if enabled)
          Verify your email if prompted
          You are redirected to: frontend/dashboard.html

STEP 6 ── Account synced to database  ✓ automatic
          The app calls POST /api/auth/sync/profile
          Your user record is created in MySQL

STEP 7 ── Upload your first document
          Click "Documents" in the sidebar  OR  click "Upload Document" on the dashboard
          Drag & drop a PDF, DOCX, or TXT file
          Status shows: Uploaded → Processing → Ready
          (Processing takes 5–15 seconds depending on file size)

STEP 8 ── Open the document
          Once status is "Ready", click the "Open" button
          You land on the document detail page

STEP 9 ── Generate a Summary
          Select a summary type (Quick / Detailed / Bullet Points / Exam Revision / Simple)
          Click "Generate Summary"
          AI generates and saves the summary

STEP 10 ── Generate Flashcards
           Set card count (10 / 20 / 30)
           Click "Generate Flashcards"
           Go to Flashcards page → flip cards → rate each one (Again / Hard / Good / Easy)
           SM-2 schedules your next review automatically

STEP 11 ── Generate a Quiz
           Choose difficulty (Easy / Medium / Hard / Mixed)
           Set question count (5–20)
           Click "Generate Quiz"
           Go to Quizzes page → take the quiz → submit
           Score saved, mastery score updated for that topic

STEP 12 ── Ask the AI Tutor
           Go to "AI Tutor" in the sidebar
           Select a learning mode (Explain / Deep Dive / Quiz Me / Socratic / Exam Prep / Summarize)
           Optionally select your document from the context dropdown
           Type your question and press Enter
           Watch the AI respond in real time (streaming)

STEP 13 ── Check your Dashboard
           Go to "Dashboard"
           See: study time, quizzes taken, flashcards reviewed, documents uploaded
           See: strong topics, weak topics, personalized recommendations

STEP 14 ── Check Analytics
           Go to "Analytics"
           See: mastery scores per topic, study streak, full activity history
```

---

## 📂 Opening the App

The frontend is plain HTML — **no npm, no build step**. Pick any one method:

### Method 1 — VS Code Live Server (recommended)

1. Open the project folder in VS Code
2. Install the **Live Server** extension if you haven't already  
   *(search "Live Server" by Ritwick Dey in Extensions)*
3. Right-click `frontend/index.html` in the file explorer
4. Click **"Open with Live Server"**
5. Browser opens automatically at `http://127.0.0.1:5500/frontend/index.html`

> Live Server auto-refreshes the page when you save any HTML/CSS/JS file.

### Method 2 — Python HTTP server

```bash
# From the project root:
cd frontend
python -m http.server 5500
```

Then open: `http://localhost:5500` in your browser.

### Method 3 — Direct file open

Simply double-click `frontend/index.html` in File Explorer.  
The app opens as a `file://` URL. This works but some browsers restrict `fetch()` on `file://` — Method 1 is safer.

### Which port does the backend expect?

By default the backend allows these frontend origins:

```
http://localhost:5500
http://127.0.0.1:5500
http://localhost:3000
http://localhost:8080
```

If you serve on a different port, add it to your `.env`:

```env
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500,http://localhost:YOUR_PORT
```

Then restart: `docker compose restart backend`

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values:

```env
# ── Required ──────────────────────────────────────────────────────────────────

# MySQL — these match the Docker Compose defaults (no change needed)
DATABASE_URL=mysql+aiomysql://study_user:study_pass@db:3306/study_buddy
MYSQL_ROOT_PASSWORD=StudyBuddy_Root_2024
MYSQL_DATABASE=study_buddy
MYSQL_USER=study_user
MYSQL_PASSWORD=study_pass

# Clerk — get from https://dashboard.clerk.com → your app → API Keys
CLERK_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxx   # also goes in every HTML <meta> tag
CLERK_SECRET_KEY=sk_test_xxxxxxxxxxxx        # backend only — never in frontend

# LLM provider key (OpenAI, Groq, Together AI, or Ollama)
LLM_API_KEY=sk-xxxxxxxxxxxx

# ── Optional ──────────────────────────────────────────────────────────────────

LLM_MODEL=gpt-4o-mini          # change for other providers
LLM_BASE_URL=                  # leave blank for OpenAI; set for Groq/Together/Ollama

STORAGE_PATH=./uploads         # where uploaded files are stored
MAX_FILE_SIZE_MB=50            # upload size limit

CORS_ORIGINS=http://localhost:3000,http://localhost:5500,http://127.0.0.1:5500

RATE_LIMIT_PER_MINUTE=60
APP_ENV=development            # set to "production" to hide API docs
LOG_LEVEL=INFO
```

---

## Running Locally (Docker)

### Start everything

```bash
docker compose up --build
```

| Service | URL | Description |
|---|---|---|
| FastAPI backend | `http://localhost:8000` | Auto-reloads on code changes |
| Swagger UI | `http://localhost:8000/docs` | Interactive API docs |
| MySQL | `localhost:3307` | Port 3307 (not 3306) |
| Health check | `http://localhost:8000/health` | `{"status":"healthy"}` |

### First-time migration

```bash
docker exec -it ai-poweredstudybuddy-backend-1 alembic upgrade head
```

### Stop

```bash
docker compose down
# Wipe DB data too:
docker compose down -v
```

### Logs

```bash
docker logs -f ai-poweredstudybuddy-backend-1   # backend
docker logs -f ai-poweredstudybuddy-db-1        # MySQL
```

---

## Running Without Docker

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt

# Update DATABASE_URL in .env to point to your local MySQL:
# DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/study_buddy

alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Database Migrations

```bash
# Apply all migrations
docker exec -it ai-poweredstudybuddy-backend-1 alembic upgrade head

# Check current version
docker exec -it ai-poweredstudybuddy-backend-1 alembic current

# Generate migration after model change
docker exec -it ai-poweredstudybuddy-backend-1 alembic revision --autogenerate -m "describe change"

# Roll back one step
docker exec -it ai-poweredstudybuddy-backend-1 alembic downgrade -1
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
quiz_answers       — Individual answer records per question
flashcards         — AI-generated flashcards with SM-2 fields
learning_progress  — Per-topic mastery scores and answer stats
study_sessions     — Activity log (tutor chats, quizzes, reviews)
```

---

## Clerk Setup

1. Go to [clerk.com](https://clerk.com) → Create a free account
2. Click **"Create application"** → name it "Study Buddy"
3. Choose sign-in options (Email + Password; Google optional)
4. Navigate to **Configure → API Keys**
5. Copy both keys:
   - **Publishable key** → `pk_test_...` → add to `.env` **and** all 10 HTML `<meta>` tags
   - **Secret key** → `sk_test_...` → add to `.env` **only** (never in frontend code)

Every HTML page has this tag — the publishable key must be filled in:

```html
<meta name="clerk-publishable-key" content="pk_test_YOUR_KEY_HERE">
```

---

## LLM Provider Setup

The backend uses the OpenAI-compatible API format. Set `LLM_API_KEY` and optionally override `LLM_BASE_URL` and `LLM_MODEL`.

### OpenAI (default)
```env
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=
```
Get key at: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

### Groq — free tier, very fast
```env
LLM_API_KEY=gsk_...
LLM_MODEL=llama-3.1-70b-versatile
LLM_BASE_URL=https://api.groq.com/openai/v1
```
Get key at: [console.groq.com](https://console.groq.com)

### Together AI — free $25 credit
```env
LLM_API_KEY=...
LLM_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo
LLM_BASE_URL=https://api.together.xyz/v1
```
Get key at: [api.together.xyz](https://api.together.xyz)

### Ollama — 100% local, no cost
```env
LLM_API_KEY=ollama
LLM_MODEL=llama3.2
LLM_BASE_URL=http://host.docker.internal:11434/v1
```
Install: [ollama.com](https://ollama.com) → then run `ollama pull llama3.2`

After changing `.env`: `docker compose restart backend`

---

## API Reference

Full interactive docs: **`http://localhost:8000/docs`**

### Auth
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/sync` | Create/return user from Clerk ID |
| `POST` | `/api/auth/sync/profile` | Upsert user profile (email, name, avatar) |

### Users
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/users/me` | Get current user profile |
| `PUT` | `/api/users/me` | Update profile |

### Documents
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/documents` | Upload document (multipart/form-data) |
| `GET` | `/api/documents` | List all user documents |
| `GET` | `/api/documents/{id}` | Get single document |
| `DELETE` | `/api/documents/{id}` | Delete document + file |

### AI Tutor
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/tutor/chat` | Stream AI response (Server-Sent Events) |

### Summaries
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/summaries` | Generate summary from document |
| `GET` | `/api/summaries` | List summaries (filter by `document_id`) |
| `GET` | `/api/summaries/{id}` | Get single summary |
| `DELETE` | `/api/summaries/{id}` | Delete summary |

### Quizzes
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/quizzes/generate` | Generate quiz from document |
| `GET` | `/api/quizzes` | List all user quizzes |
| `GET` | `/api/quizzes/{id}` | Get quiz with questions |
| `POST` | `/api/quizzes/{id}/attempt` | Submit answers → receive score |
| `DELETE` | `/api/quizzes/{id}` | Delete quiz |

### Flashcards
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/flashcards/generate` | Generate flashcards from document |
| `GET` | `/api/flashcards` | List flashcards (supports `due_only=true`) |
| `POST` | `/api/flashcards/{id}/review` | Record SM-2 review (quality 0–5) |
| `DELETE` | `/api/flashcards/{id}` | Delete flashcard |

### Learning & Analytics
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/learning/progress` | Topic mastery scores |
| `GET` | `/api/learning/recommendations` | Personalized study suggestions |
| `GET` | `/api/analytics/summary` | Full dashboard stats + streak |

---

## Project Structure

```
AI-Powered-Study-Buddy/
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, middleware, all routers
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic settings (env vars)
│   │   │   ├── security.py          # Clerk JWT verification (JWKS)
│   │   │   ├── exceptions.py        # Custom exceptions + global handlers
│   │   │   └── logging.py           # Structured JSON / human-readable logging
│   │   ├── api/
│   │   │   ├── deps.py              # Shared FastAPI dependencies
│   │   │   └── routes/              # One file per feature area
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── documents.py
│   │   │       ├── tutor.py
│   │   │       ├── summaries.py
│   │   │       ├── quizzes.py
│   │   │       ├── flashcards.py
│   │   │       ├── learning.py
│   │   │       └── analytics.py
│   │   ├── models/                  # SQLAlchemy ORM models (10 tables)
│   │   │   ├── user.py
│   │   │   ├── document.py
│   │   │   ├── summary.py
│   │   │   ├── topic.py
│   │   │   ├── quiz.py
│   │   │   ├── quiz_question.py
│   │   │   ├── quiz_attempt.py
│   │   │   ├── flashcard.py
│   │   │   ├── learning_progress.py
│   │   │   └── study_session.py
│   │   ├── schemas/                 # Pydantic v2 request/response schemas
│   │   ├── services/
│   │   │   ├── document_service.py  # Background PDF/DOCX/TXT extraction
│   │   │   ├── learning_service.py  # Mastery score (weighted avg) calculation
│   │   │   └── session_service.py   # Study session activity logging
│   │   ├── utils/
│   │   │   ├── pdf_parser.py        # Text extraction (pypdf, python-docx)
│   │   │   └── validators.py        # File MIME + extension validation
│   │   ├── db/
│   │   │   ├── base_class.py        # SQLAlchemy DeclarativeBase (no model imports)
│   │   │   ├── base.py              # Imports all models for Alembic discovery
│   │   │   └── session.py           # Async engine + get_db() dependency
│   │   └── prompts/                 # LLM system prompts as .txt files
│   │       ├── tutor.txt
│   │       ├── summarization.txt
│   │       ├── flashcards.txt
│   │       ├── quiz_generation.txt
│   │       └── recommendations.txt
│   ├── alembic/
│   │   └── versions/
│   │       └── 001_initial_migration.py
│   ├── alembic.ini
│   ├── Dockerfile                   # Multi-stage Python 3.12 image
│   └── requirements.txt
│
├── frontend/
│   ├── index.html                   # Landing page (public)
│   ├── dashboard.html               # Main student dashboard
│   ├── tutor.html                   # AI tutor streaming chat
│   ├── documents.html               # Upload & manage documents
│   ├── document.html                # Per-document actions
│   ├── flashcards.html              # SM-2 flashcard review
│   ├── quizzes.html                 # Quiz generation & taking
│   ├── analytics.html               # Learning analytics
│   ├── settings.html                # Profile & theme preferences
│   ├── auth/
│   │   └── signin.html              # Clerk sign-in widget
│   └── assets/
│       ├── css/styles.css           # Animations, flashcard flip, toasts
│       └── js/
│           ├── api.js               # Centralized fetch client + SSE streaming
│           ├── auth.js              # Clerk SDK wrapper + redirect guards
│           ├── ui.js                # Toast, skeleton loading, empty states
│           ├── utils.js             # Markdown renderer, formatters, debounce
│           ├── dashboard.js
│           ├── tutor.js
│           ├── documents.js
│           ├── flashcards.js
│           ├── quizzes.js
│           ├── analytics.js
│           └── settings.js
│
├── tests/                           # Pytest — 73 tests, 0 failures
│   ├── conftest.py
│   ├── test_document_processing.py  # Text extraction logic
│   ├── test_quiz_scoring.py         # Scoring, SM-2, mastery calculation
│   ├── test_security.py             # Auth guards, ownership, file checks
│   └── test_validators.py           # Extension/MIME/filename validation
│
├── scripts/
│   └── init.sql                     # MySQL utf8mb4 charset init
│
├── docs/
│   └── architecture.md              # Detailed architecture docs
│
├── docker-compose.yml               # Backend + MySQL services
├── .env.example                     # Safe template — copy to .env
├── pytest.ini
└── README.md
```

---

## Testing

```bash
# Run all 73 tests
cd backend
python -m pytest ../tests/ -v

# Single file
python -m pytest ../tests/test_quiz_scoring.py -v

# With coverage
python -m pytest ../tests/ --cov=app --cov-report=term-missing
```

| Test file | Tests | Coverage area |
|---|---|---|
| `test_quiz_scoring.py` | 25 | Quiz scoring, SM-2 algorithm, mastery calculation |
| `test_document_processing.py` | 13 | Text extraction, clean text, MIME dispatch |
| `test_security.py` | 14 | Auth guards, ownership logic, file security |
| `test_validators.py` | 21 | Extension validation, MIME check, filename sanitisation |

---

## Troubleshooting

### Backend won't start — `SettingsError` on `CORS_ORIGINS`
The `.env` file is empty or the variable is malformed.
```bash
# Fix: ensure .env has this line (no spaces around commas)
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
# Then:
docker compose restart backend
```

### Backend container shows "unhealthy"
```bash
# See the real error
docker logs ai-poweredstudybuddy-backend-1 --tail 50
# After fixing, restart
docker compose restart backend
```

### Clerk widget doesn't appear on sign-in page
- Check that `<meta name="clerk-publishable-key" content="pk_test_...">` is filled in the HTML.
- Open browser DevTools (F12) → Console — a wrong key shows `ClerkJS: Invalid publishable key`.

### `User account not found` API error
The user hasn't been synced to MySQL yet.  
**Fix:** Sign out and sign back in — the sync runs automatically on sign-in.

### Document stays at "Processing" forever
```bash
docker logs ai-poweredstudybuddy-backend-1 | grep -i "process_document"
```
Usually caused by a corrupt file or unsupported encoding. Try a different document.

### MySQL "connection refused"
```bash
docker ps   # check if db container is healthy
docker logs ai-poweredstudybuddy-db-1 --tail 20
```
MySQL can take up to 60 seconds on the very first start.

### Alembic — `Table already exists`
```bash
docker exec -it ai-poweredstudybuddy-backend-1 alembic downgrade base
docker exec -it ai-poweredstudybuddy-backend-1 alembic upgrade head
```

### CORS error in browser (`blocked by CORS policy`)
Your frontend is running on a port not listed in `CORS_ORIGINS`.
```env
# Add your port to .env:
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500,http://localhost:YOUR_PORT
```
```bash
docker compose restart backend
```

### AI features return error (quiz generation, summaries, etc.)
Your `LLM_API_KEY` is missing or has no credits.
```bash
# Check the .env
grep LLM_API_KEY .env
# After adding/fixing the key:
docker compose restart backend
```

---

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feat/your-feature`
3. Commit your changes following the format below
4. Push: `git push origin feat/your-feature`
5. Open a Pull Request

### Commit message format

```
feat:     add new feature
fix:      resolve a bug
docs:     update documentation only
refactor: code improvement without behaviour change
test:     add or update tests
chore:    maintenance, dependency updates
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ using FastAPI, Tailwind CSS, and OpenAI

**[⬆ Back to top](#-ai-powered-study-buddy)**

</div>
