"""
FastAPI wrapper for Oasis OS — Multi-Agent Calendar Assistant.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from auth import check_auth_status
from graph import app as langgraph_app
from nodes import get_suggested_slots
from tools import create_calendar_event, delete_calendar_event, fetch_calendar_events

api = FastAPI(title="Oasis OS API", version="2.0.0")

# CORS: default localhost; set CORS_ORIGINS (comma-separated) in production for frontend URL(s)
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173")
_cors_list = [o.strip() for o in _cors_origins.split(",") if o.strip()]

api.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request / Response models ---

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
    summary_horizon: Optional[str] = "daily"


class EventAttendee(BaseModel):
    email: str = ""
    displayName: str = ""


class CalendarEvent(BaseModel):
    id: str = ""
    summary: str
    start: str
    end: str = ""
    account: str
    attendees: Optional[List[EventAttendee]] = None
    description: str = ""
    category: str = "fixed"


class ChatResponse(BaseModel):
    final_decision: str
    needs_booking_ui: bool
    needs_floating_vs_fixed_choice: Optional[bool] = False
    parsed_task: ParsedTask
    existing_events: Optional[dict] = None
    suggested_slots: Optional[List[SuggestedSlot]] = None
    query_events: Optional[List[dict]] = None
    summary_horizon: Optional[str] = "daily"


class BookRequest(BaseModel):
    title: str
    date: str
    start_time: str
    end_time: Optional[str] = None
    account_id: str
    category: Optional[str] = "fixed"
    description: Optional[str] = ""


class BookResponse(BaseModel):
    ok: bool
    event_link: Optional[str] = None
    message: str


class DeleteEventRequest(BaseModel):
    account_id: str  # "work" or "personal"
    event_id: str


class DeleteEventResponse(BaseModel):
    ok: bool
    message: str


class BookingSlotsRequest(BaseModel):
    """When user chose 'Assign a time' — get suggested slots for that task's date."""
    parsed_task: ParsedTask


class BookingSlotsResponse(BaseModel):
    needs_booking_ui: bool = True
    suggested_slots: List[SuggestedSlot]
    parsed_task: ParsedTask


# --- Helpers ---

def _group_events_by_account(events: list) -> dict:
    work = [e for e in events if e.get("account") == "work"]
    personal = [e for e in events if e.get("account") == "personal"]
    return {"work": work, "personal": personal}


# --- Endpoints ---

@api.get("/events")
def get_events_for_day(date: str):
    """
    Fetch calendar events for a single day. Google API only — no LLM, no graph.
    Use this when the user clicks a date (e.g. in month view) to load that day's schedule.
    """
    if not date or len(date) != 10:
        raise HTTPException(status_code=400, detail="Query param 'date' required as YYYY-MM-DD")
    try:
        events = fetch_calendar_events(["work", "personal"], date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"date": date, "existing_events": _group_events_by_account(events)}


@api.get("/health")
def health():
    return {"status": "ok", "service": "oasis-os", "version": "2.0.0"}


@api.get("/auth/status")
def auth_status():
    return check_auth_status()


@api.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        result = langgraph_app.invoke({"user_input": req.user_input})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    parsed = result.get("parsed_task", {})
    events = result.get("existing_events", [])
    suggested = result.get("suggested_slots", [])
    query_events = result.get("query_events", [])
    horizon = result.get("summary_horizon", parsed.get("summary_horizon", "daily"))

    existing_grouped = _group_events_by_account(events) if events else None

    return ChatResponse(
        final_decision=result.get("final_decision", ""),
        needs_booking_ui=result.get("needs_booking_ui", False),
        needs_floating_vs_fixed_choice=result.get("needs_floating_vs_fixed_choice", False),
        parsed_task=ParsedTask(
            title=parsed.get("title", ""),
            date=parsed.get("date", ""),
            start_time=parsed.get("start_time"),
            end_time=parsed.get("end_time"),
            category=parsed.get("category", "floating"),
            account_id=parsed.get("account_id", "personal"),
            intent=parsed.get("intent", "summarize"),
            summary_horizon=parsed.get("summary_horizon", "daily"),
        ),
        existing_events=existing_grouped,
        suggested_slots=[SuggestedSlot(**s) for s in suggested] if suggested else None,
        query_events=query_events if query_events else None,
        summary_horizon=horizon,
    )


@api.post("/book", response_model=BookResponse)
def book(req: BookRequest):
    if req.account_id not in ("work", "personal"):
        return BookResponse(ok=False, message="account_id must be 'work' or 'personal'")

    start_str = f"{req.date} {req.start_time}"
    end_str = f"{req.date} {req.end_time}" if req.end_time else None

    try:
        link = create_calendar_event(
            req.account_id,
            req.title,
            start_str,
            end_str,
            description=req.description or "",
            category=req.category or "fixed",
        )
        return BookResponse(ok=True, event_link=link, message="Event created successfully.")
    except Exception as e:
        return BookResponse(ok=False, message=str(e))


@api.post("/booking/slots", response_model=BookingSlotsResponse)
def booking_slots(req: BookingSlotsRequest):
    """
    User chose "Assign a time" for a booking. Fetch events for that date and return
    suggested slots (no LLM). Frontend then shows the booking panel with these slots.
    """
    task = req.parsed_task
    date = task.date or ""
    if not date or len(date) != 10:
        raise HTTPException(status_code=400, detail="parsed_task.date required as YYYY-MM-DD")
    try:
        events = fetch_calendar_events(["work", "personal"], date)
        slots = get_suggested_slots(date, events)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return BookingSlotsResponse(
        needs_booking_ui=True,
        suggested_slots=[SuggestedSlot(**s) for s in slots],
        parsed_task=task,
    )


@api.post("/event/delete", response_model=DeleteEventResponse)
def delete_event(req: DeleteEventRequest):
    """Cancel/delete a calendar event. Only works for events that exist in Google Calendar (fixed events)."""
    if req.account_id not in ("work", "personal"):
        return DeleteEventResponse(ok=False, message="account_id must be 'work' or 'personal'")
    if not req.event_id:
        return DeleteEventResponse(ok=False, message="event_id is required")
    try:
        delete_calendar_event(req.account_id, req.event_id)
        return DeleteEventResponse(ok=True, message="Event cancelled.")
    except Exception as e:
        return DeleteEventResponse(ok=False, message=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000)
