"""
FastAPI wrapper for Oasis OS — Multi-Agent Calendar Assistant.
Exposes REST endpoints for the React frontend.
"""
import os
import sys

# Ensure parent directory is on path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List

from app import app as langgraph_app
from tools import create_calendar_event
from auth import check_auth_status

api = FastAPI(title="Oasis OS API", version="1.0.0")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---

class ChatRequest(BaseModel):
    user_input: str
    timezone: Optional[str] = None


class SuggestedSlot(BaseModel):
    start_time: str
    end_time: str
    account_suggestions: Optional[List[str]] = None


class ParsedTask(BaseModel):
    title: str
    date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    category: str
    account_id: str
    intent: str


class ChatResponse(BaseModel):
    final_decision: str
    needs_booking_ui: bool
    parsed_task: ParsedTask
    existing_events: Optional[dict] = None  # { work: [...], personal: [...] }
    suggested_slots: Optional[List[SuggestedSlot]] = None
    query_events: Optional[List[dict]] = None


class BookRequest(BaseModel):
    title: str
    date: str
    start_time: str  # HH:MM
    end_time: Optional[str] = None  # HH:MM, defaults to +1h
    account_id: str  # "work" or "personal"
    category: Optional[str] = None


class BookResponse(BaseModel):
    ok: bool
    event_link: Optional[str] = None
    message: str


# --- Helpers ---

def _group_events_by_account(events: list) -> dict:
    work = [e for e in events if e.get("account") == "work"]
    personal = [e for e in events if e.get("account") == "personal"]
    return {"work": work, "personal": personal}


# --- Endpoints ---

@api.get("/health")
def health():
    """Health check for load balancers and dev sanity."""
    return {"status": "ok", "service": "oasis-os"}


@api.get("/auth/status")
def auth_status():
    """Returns auth status for work and personal Google accounts."""
    return check_auth_status()


@api.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Process user input through the LangGraph workflow.
    Returns structured response for chat, booking UI, agenda, or query results.
    """
    try:
        result = langgraph_app.invoke({"user_input": req.user_input})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    parsed = result.get("parsed_task", {})
    events = result.get("existing_events", [])
    suggested = result.get("suggested_slots", [])
    query_events = result.get("query_events", [])

    # Group existing_events by account
    existing_grouped = _group_events_by_account(events) if events else None

    return ChatResponse(
        final_decision=result.get("final_decision", ""),
        needs_booking_ui=result.get("needs_booking_ui", False),
        parsed_task=ParsedTask(
            title=parsed.get("title", ""),
            date=parsed.get("date", ""),
            start_time=parsed.get("start_time"),
            end_time=parsed.get("end_time"),
            category=parsed.get("category", "floating"),
            account_id=parsed.get("account_id", "personal"),
            intent=parsed.get("intent", "summarize"),
        ),
        existing_events=existing_grouped,
        suggested_slots=[SuggestedSlot(**s) for s in suggested] if suggested else None,
        query_events=query_events if query_events else None,
    )


@api.post("/book", response_model=BookResponse)
def book(req: BookRequest):
    """
    Create a calendar event in the specified account.
    """
    if req.account_id not in ("work", "personal"):
        return BookResponse(ok=False, message="account_id must be 'work' or 'personal'")

    start_str = f"{req.date} {req.start_time}"
    end_str = f"{req.date} {req.end_time}" if req.end_time else None

    try:
        link = create_calendar_event(req.account_id, req.title, start_str, end_str)
        return BookResponse(ok=True, event_link=link, message="Event created successfully.")
    except Exception as e:
        return BookResponse(ok=False, message=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000)
