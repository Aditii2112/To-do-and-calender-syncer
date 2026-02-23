# Oasis OS — Run Instructions

## Quick Start (one command)

From the project root (`To-do-and-calender-syncer/`):

```bash
npm install
npm run dev
```

This starts both the FastAPI backend (port 8000) and the React frontend (port 5173).

---

## File Tree

```
To-do-and-calender-syncer/         # Project root
├── api/
│   ├── __init__.py
│   └── main.py                    # FastAPI wrapper
├── app.py                         # LangGraph state machine
├── auth.py                        # OAuth for Work/Personal
├── parser.py                      # Gemini intent parsing
├── tools.py                       # Calendar fetch/create/search
├── requirements.txt
├── API_README.md
├── (credentials.json, token_work.json, token_personal.json, .env)
│
├── oasis-frontend/                # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts          # chat(), book()
│   │   ├── components/
│   │   │   ├── AppShell.tsx
│   │   │   ├── ChatPane.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── BookingPanel.tsx
│   │   │   ├── SuggestedSlotsList.tsx
│   │   │   ├── AgendaView.tsx
│   │   │   └── QueryResultsView.tsx
│   │   ├── App.tsx
│   │   ├── App.css
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.ts             # Proxies /api to backend
│   └── FRONTEND_README.md
│
├── FRONTEND_README.md
├── package.json                   # Root: npm run dev runs both
└── RUN.md                         # This file
```

## Step 1: Backend Setup

```bash
pip install -r requirements.txt
```

Ensure you have:
- `credentials.json` (Google Cloud OAuth client)
- `.env` with `GOOGLE_API_KEY=your_gemini_api_key`
- Run `python auth.py` once to generate `token_work.json` and `token_personal.json`

## Step 2: Start Backend

```bash
uvicorn api.main:api --reload --host 0.0.0.0 --port 8000
```

Backend runs at http://localhost:8000

## Step 3: Frontend Setup & Start

```bash
cd oasis-frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173

The Vite dev server proxies `/api/*` to `http://localhost:8000/*`.

## Step 4: Use the App

1. Open http://localhost:5173
2. Try:
   - "What's my day look like tomorrow?" → summarize
   - "When can I schedule gym tomorrow?" → create + booking UI
   - "When did I last do laundry?" → query

## API Base URL (Frontend)

- Dev: `/api` (proxied automatically)
- Override: create `oasis-frontend/.env` with `VITE_API_BASE=http://localhost:8000`
