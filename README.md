# Oasis OS

A Multi-Agent Orchestrator for Intelligent Scheduling and Daily Briefings.

Demo: https://drive.google.com/file/d/1VLfXz6QnrCsShMmZGhLbvCBUfv-3zYyc/view?usp=sharing

---

## Overview (what it does and how it works)

**What it does**  
Oasis OS is a calendar assistant: you chat in natural language; it shows summaries, answers “when did I meet X?”, and lets you add tasks (floating or fixed). Fixed events go to Google Calendar; floating ones stay in the UI (and in the browser via localStorage).

**Flow (high level)**  
1. You type a message → the backend **parses** it (intent + date; rules plus optional LLM).  
2. **Intent** decides the path:  
   - **Query** → search calendar (Google + semantic) → show past/next events.  
   - **Summarize** → fetch events for day/week/month/year → build summary (no extra LLM).  
   - **Create** → ask “Floating or assign a time?” → if assign time: fetch day, suggest slots, then book to Google.  
3. Clicking a date in the calendar only calls the **Google Calendar API** (no LLM).

**Tech stack**  
- **Backend:** Python, FastAPI, LangGraph (state graph + nodes: parse, query, fetch, resolve, summarize, write).  
- **LLM:** Groq (free, high limit), local Ollama, or Google Gemini — used only for **parsing** (intent + time); Pydantic structures the output; rules normalize dates and query titles.  
- **Calendar:** Google Calendar API (OAuth, work + personal).  
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS; chat + calendar side by side; floating tasks in localStorage.

**Repo layout**  
- Monorepo: `backend/` (FastAPI + LangGraph + `api/main.py`), `frontend/` (Vite + React).  
- One command: `npm run dev` runs backend (uvicorn) and frontend (Vite) together.

---

## How others can use it

Anyone who wants to run Oasis OS needs to do the following once.

1. **Clone and install**
   ```bash
   git clone <your-repo-url>
   cd To-do-and-calender-syncer
   npm install
   cd backend && python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cd ../frontend && npm install
   ```

2. **Google Calendar access (required)**  
   - In [Google Cloud Console](https://console.cloud.google.com/): create a project, enable **Google Calendar API**, create an **OAuth 2.0 Client ID** (Desktop app), download the JSON.  
   - Save that file as `backend/credentials.json`.  
   - On first run (or when you run `cd backend && python auth.py`), a browser will open to sign in to Google; choose Work and Personal accounts. That creates `token_work.json` and `token_personal.json` in `backend/`.  
   - These files are in `.gitignore`; each user sets up their own.

3. **LLM (choose one)** — Parser uses: **Groq** (if set) → **Ollama** (if local) → **Gemini**.
   - **Groq (recommended for ~100 users, free):** Get an API key from [Groq Console](https://console.groq.com), then in `backend/.env` add:
     ```
     GROQ_API_KEY=your_key_here
     ```
     Free tier ~14,400 requests/day. Optional: `GROQ_MODEL=llama3-8b-8192` for a faster, smaller model.
   - **Ollama (local, no key):** Install [Ollama](https://ollama.com), run `ollama pull qwen2.5:0.5b`, then in `backend/.env` add:
     ```
     USE_LOCAL_LLM=true
     ```
   - **Gemini:** Get a key from [Google AI Studio](https://aistudio.google.com/apikey), then in `backend/.env` add:
     ```
     GOOGLE_API_KEY=your_key_here
     ```

4. **Run**
   ```bash
   npm run dev
   ```
   - Backend: `http://localhost:8000`  
   - Frontend: `http://localhost:5173` (open this in the browser)

After that, they use the chat and calendar UI; floating tasks persist in that browser via localStorage. To share the app publicly you’d deploy the frontend (e.g. Vercel) and backend (e.g. Railway) and set env vars as in the sections below.

---

## Architecture

The agent is a LangGraph **StateGraph** that routes tasks through specialized nodes based on parsed intent:

```
parse → route_intent ─┬─ "query"  → query     → write → END
                       └─ "fetch"  → fetch ─┬─ "summarize" → summarize → write → END
                                             └─ "resolve"  → resolve   → write → END
```

| Node | What it does |
|---|---|
| **parse** | Gemini structured output → intent, category, horizon |
| **query** | Google Calendar search + in-memory semantic search (attendees, descriptions) |
| **fetch** | Pulls full events (attendees, description, category) for a date or range |
| **resolve** | Inverse Availability — computes free blocks, suggests slots for floating tasks |
| **summarize** | Daily / Weekly / Monthly / Yearly summaries from state (no LLM calls) |
| **write** | Formats final output, decides whether to show booking UI |

### Intent model (user query types)

User queries are classified into three intents; **time** is resolved relative to “today” (no LLM needed for that):

| Intent | Examples | What runs |
|--------|----------|-----------|
| **Summarization** | “Summarize my week”, “What does my day look like?”, “Summarize the month” | Day / week / month / year horizon → fetch range → summarize from state (no extra LLM) |
| **Query** | “When did I last meet Prof Lee?”, “When am I meeting Mr X next?” | Semantic search over calendar (attendees, titles, descriptions) → answer from events |
| **Booking** | “Laundry tomorrow”, “Coffee chat on Monday” | Create task; optional: ask “Floating or assign a time?” to avoid guessing fixed vs floating |

**Clicking a date in the calendar** does **not** call the LLM: the frontend calls `GET /events?date=YYYY-MM-DD`, which uses only the Google Calendar API to load that day’s events.

## Tech Stack

- **Orchestration:** LangGraph (StateGraph)
- **LLM:** Groq (default) / Ollama (local) / Gemini — parsing only
- **Backend:** Python, FastAPI
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4
- **Calendar API:** Google Calendar REST API (OAuth 2.0)
- **Requires:** Python 3.10+, Node 18+

## File Structure

```
To-do-and-calender-syncer/
├── package.json                  # Monorepo scripts (runs both backend + frontend)
│
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py               # FastAPI: /chat, /book, /events?date=, /health, /auth/status
│   ├── state.py                   # AgentState TypedDict
│   ├── graph.py                   # LangGraph StateGraph definition + routing
│   ├── nodes.py                   # Node implementations (parse, query, fetch, resolve, summarize, write)
│   ├── tools.py                   # Google Calendar API calls, semantic search
│   ├── parser.py                  # Gemini intent parsing → Task model
│   ├── auth.py                    # OAuth for Work / Personal accounts
│   ├── app.py                     # Re-exports graph.app for backward compat
│   ├── streamlit.py               # Optional Streamlit UI
│   └── requirements.txt
│
└── frontend/
    ├── package.json               # Frontend deps (React, Tailwind, Vite)
    ├── vite.config.ts             # Proxies /api → localhost:8000
    └── src/
        ├── main.tsx
        ├── App.tsx                # Side-by-side layout: Chat + Calendar
        ├── index.css              # Tailwind v4 entry + theme
        ├── api/
        │   └── client.ts          # chat(), book() API client + types
        └── components/
            ├── AppShell.tsx        # Top-level shell + header
            ├── ChatPane.tsx        # Chat interface with quick actions
            ├── CalendarView.tsx    # Visual calendar: timeline, color-coded events
            ├── MessageBubble.tsx   # User / assistant message bubbles
            ├── BookingPanel.tsx    # Time picker + confirm → creates event
            ├── SuggestedSlotsList.tsx
            ├── AgendaView.tsx      # Horizon-aware agenda cards
            └── QueryResultsView.tsx
```

## Prerequisites

You need **two things** from Google Cloud before the app can talk to your calendars:

### 1. `credentials.json` (Google Cloud OAuth Client)

This is a standard OAuth 2.0 client secret file. It does NOT contain your calendar data — it just identifies your app to Google so it can request permission.

**How to get it:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use an existing one)
3. Enable the **Google Calendar API**
4. Go to **Credentials** → **Create Credentials** → **OAuth client ID**
5. Application type: **Desktop app**
6. Download the JSON and save it as `backend/credentials.json`

### 2. `GOOGLE_API_KEY` (Gemini API key)

Used by the parser to call Gemini for intent classification.

**How to get it:**
1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key
3. Save it in `backend/.env`:
   ```
   GOOGLE_API_KEY=your_key_here
   ```

### 2b. Optional: Local model (no API key, no quota)

To avoid API limits entirely, you can run a **small local model** with [Ollama](https://ollama.com):

1. **Install Ollama:** [ollama.com](https://ollama.com) (or `brew install ollama` on macOS).
2. **Pull a small model** (one-time, ~300MB–1GB):
   ```bash
   ollama pull qwen2.5:0.5b
   ```
   Other options: `ollama pull gemma2:2b` or `ollama pull llama3.2:1b`.
3. **Use it in this app:** in `backend/.env` add:
   ```
   USE_LOCAL_LLM=true
   ```
   Optional: `OLLAMA_MODEL=gemma2:2b` (default is `qwen2.5:0.5b`).

The parser will use the local model instead of Gemini. No API key needed when `USE_LOCAL_LLM=true`.

### 3. Token files (auto-generated)

On first run, the app opens a browser window asking you to sign in to Google. This generates `token_work.json` and `token_personal.json` in `backend/`. You can also run `python auth.py` manually to set these up beforehand.

**All of these files are in `.gitignore` and will never be committed.**

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Place `credentials.json` in `backend/` and set one LLM in `backend/.env` (e.g. `GROQ_API_KEY=...` or `USE_LOCAL_LLM=true` — see "How others can use it").

### Frontend

```bash
cd frontend
npm install
```

### Run (one command from root)

```bash
npm install   # first time only, installs concurrently
npm run dev
```

This starts:
- FastAPI backend on `http://localhost:8000`
- React frontend on `http://localhost:5173` (proxies `/api/*` to backend)

Or run them separately:
```bash
npm run dev:backend    # just the API
npm run dev:frontend   # just the UI
```

## API Endpoints

### `GET /health`
```json
{ "status": "ok", "service": "oasis-os", "version": "2.0.0" }
```

### `GET /auth/status`
```json
{ "work": true, "personal": false }
```

### `POST /chat`

**Request:**
```json
{ "user_input": "Summarize my week" }
```

**Response:**
```json
{
  "final_decision": "📆 Weekly Summary (2026-03-02 → 2026-03-08): ...",
  "needs_booking_ui": false,
  "parsed_task": {
    "title": "week",
    "date": "2026-03-05",
    "category": "floating",
    "account_id": "personal",
    "intent": "summarize",
    "summary_horizon": "weekly"
  },
  "existing_events": { "work": [...], "personal": [...] },
  "summary_horizon": "weekly"
}
```

### `POST /book`

Only called when the user explicitly confirms a time in the Booking UI. Floating tasks stay off the calendar until a time is assigned.

**Request:**
```json
{
  "title": "Gym",
  "date": "2026-03-06",
  "start_time": "11:00",
  "end_time": "12:00",
  "account_id": "personal",
  "category": "floating"
}
```

**Response:**
```json
{
  "ok": true,
  "event_link": "https://www.google.com/calendar/event?eid=...",
  "message": "Event created successfully."
}
```

## Usage Examples

| You say | Intent | What happens |
|---|---|---|
| "What does my day look like?" | summarize (daily) | Fetches today's events, shows agenda |
| "Summarize my month" | summarize (monthly) | Fetches full month, groups by week |
| "When can I schedule gym tomorrow?" | create (floating) | Shows free slots, booking UI |
| "Meeting with Prof Lee at 3pm Friday" | create (fixed) | Pre-fills 3:00 PM, shows confirm |
| "When did I last meet Prof Lee?" | query | Semantic search across attendees + descriptions |

## Deploy frontend to Vercel

1. Import the repo in [Vercel](https://vercel.com); set **Root Directory** to `frontend`.
2. In Project Settings → Environment Variables, add `VITE_API_BASE` with your backend API URL (e.g. `https://your-backend.fly.dev` or `https://api.yourdomain.com`). For local dev the app uses `/api` (proxied to localhost).
3. Deploy; the build uses `frontend/vercel.json` (Vite, output `dist/`). The deployed site will call the API at `VITE_API_BASE`.

## Backend deploy and environment

Run the backend on a host that supports long-running processes and (if you keep file-based auth) writable disk (e.g. Render, Fly.io, or a VPS). Do **not** set `USE_LOCAL_LLM` in production; use **Groq** (recommended) or **Gemini** and set the corresponding API key.

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Recommended for production (free, ~14k req/day). Parser uses Groq if set. |
| `GOOGLE_API_KEY` | Alternative: Gemini for parser. Used if `GROQ_API_KEY` is not set. |
| `CORS_ORIGINS` | Comma-separated allowed origins (e.g. `https://your-app.vercel.app`). Defaults to localhost if unset. |
| `USE_LOCAL_LLM` | Set to `true` only for local dev with Ollama; leave unset in production. |

OAuth tokens (`token_work.json`, `token_personal.json`) and `credentials.json` must be available to the backend (e.g. on the server filesystem after a one-time OAuth flow, or via a web OAuth flow and a token store). See the architecture plan for production auth options.

## Security

This repository does **not** contain tokens or credentials. You must provide your own `credentials.json`, `.env`, and token files locally. All are excluded via `.gitignore`.
