
# 📅 Oasis OS
A Multi-Agent Orchestrator for Intelligent Scheduling and Daily Briefings

Demo: https://drive.google.com/file/d/1VLfXz6QnrCsShMmZGhLbvCBUfv-3zYyc/view?usp=sharing

Built with LangGraph, Google Gemini, and the Google Calendar API. This agent goes beyond simple scheduling by analyzing user intent, managing cross-account availability (Work/Personal), and providing structured daily briefings.

**System Architecture**
The agent is built as a Stateful Graph. Instead of a linear script, it uses a state machine to route tasks based on the user's natural language.

**How it Works: The Node Logic**
parser_node: Uses Gemini to transform raw text into a structured JSON task object (Identifying Intent: create, query, or summarize).

query_node: Specialized for historical searches. It looks across both Work and Personal accounts to find the last time a specific event occurred.

fetcher_node: A middleware node that retrieves all events for a target date to populate the agent's "short-term memory."

resolver_node: Calculates the Inverse Availability. Instead of just showing busy blocks, it identifies the "Smart Gaps" where you are actually free to meet.

summarizer_node: Formats a clean, distraction-free agenda for the day, separated by account.

writer_node: The final state-setter that triggers the Streamlit UI to render interactive booking widgets.


![Workflow Graph](/assets/my_workflow_graph.png)

Multi-agent orchestrator workflow.


# Features
Dual-Account Sync: Simultaneously fetches and manages data from generic Work and Personal Google Calendar accounts.

Intent-Based Routing: Automatically distinguishes between "What's my day look like?" (Summary) and "When did I last do laundry?" (Query).

Interactive Web UI: A Streamlit frontend that replaces terminal prompts with a modern chat interface and time-picker widgets.

No-AI Summarization: Optimized for performance. Once data is fetched, the briefing is generated via logic rather than extra LLM calls to save on latency.

# Tech Stack

- Orchestration: LangGraph (StateGraph)
- LLM: Google Gemini (free-tier friendly)
- Backend: Python (FastAPI + LangGraph) in `backend/`
- Frontend: React + TypeScript (Vite) in `frontend/`
- API: Google Calendar REST API
- Environment: Python 3.10+, Node 18+

# Installation & Setup (Monorepo)

Clone the repo:

```bash
git clone https://github.com/Aditii2112/To-do-and-calender-syncer.git
cd To-do-and-calender-syncer
```

## Backend setup (`backend/`)

```bash
cd backend
pip install -r requirements.txt
```

Google API setup:

- Enable Google Calendar API in Google Cloud Console.
- Download `credentials.json` and place it in the `backend/` folder.
- On the first run, the app will open a browser to generate `token_work.json` and `token_personal.json` in `backend/`.

Environment variables: create a `.env` file in `backend/`:

```bash
GOOGLE_API_KEY=your_gemini_api_key_here
```

Start the API server:

```bash
uvicorn api.main:api --reload --host 0.0.0.0 --port 8000
```

## Frontend setup (`frontend/`)

From the repo root:

```bash
cd frontend
npm install
npm run dev
```

The React app runs at `http://localhost:5173` and proxies `/api/*` to the backend at `http://localhost:8000`.

## One-command dev startup (root)

From the repo root (`To-do-and-calender-syncer/`):

```bash
npm install
npm run dev
```

This starts both:

- FastAPI backend on port `8000`
- React frontend on port `5173`

## Security Note

This repository does not contain private tokens or credentials.  
You must provide your own `backend/credentials.json`, `.env`, and token files locally. These paths are ignored via `.gitignore` and will not be pushed.
