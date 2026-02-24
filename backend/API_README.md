# Oasis OS API

FastAPI wrapper for the LangGraph calendar agent.

## Run

From `backend/`:

```bash
pip install -r requirements.txt
uvicorn api.main:api --reload --host 0.0.0.0 --port 8000
```

## Endpoints

### GET /health

Health check.

**Response:**
```json
{ "status": "ok", "service": "oasis-os" }
```

### GET /auth/status

Auth status for Work and Personal Google accounts.

**Response:**
```json
{ "work": true, "personal": true }
```

### POST /chat

Process user input through the LangGraph workflow.

**Request:**
```json
{
  "user_input": "What's my day look like tomorrow?",
  "timezone": "America/Los_Angeles"
}
```

**Response (summarize):**
```json
{
  "final_decision": "📅 Agenda for 2025-02-21:\n...",
  "needs_booking_ui": false,
  "parsed_task": {
    "title": "day look",
    "date": "2025-02-21",
    "start_time": null,
    "end_time": null,
    "category": "floating",
    "account_id": "personal",
    "intent": "summarize"
  },
  "existing_events": {
    "work": [{"summary": "Meeting", "start": "2025-02-21T10:00:00", "end": "2025-02-21T11:00:00", "account": "work"}],
    "personal": []
  },
  "suggested_slots": null,
  "query_events": null
}
```

**Response (create):**
```json
{
  "final_decision": "🗓️ Schedule for 2025-02-21:\n\n🚫 OCCUPIED BLOCKS:\n • 10:00 AM - 11:00 AM\n\n🟢 BEST TIMES TO SCHEDULE:\n • 09:00 AM - 10:00 AM\n • 11:00 AM - 07:00 PM",
  "needs_booking_ui": true,
  "parsed_task": {
    "title": "gym",
    "date": "2025-02-21",
    "start_time": null,
    "end_time": null,
    "category": "floating",
    "account_id": "personal",
    "intent": "create"
  },
  "existing_events": {...},
  "suggested_slots": [
    {"start_time": "09:00", "end_time": "10:00", "account_suggestions": ["work", "personal"]},
    {"start_time": "11:00", "end_time": "19:00", "account_suggestions": ["work", "personal"]}
  ],
  "query_events": null
}
```

**Response (query):**
```json
{
  "final_decision": "✅ Not currently scheduled. Last occurrence: 2025-02-15 (personal).",
  "needs_booking_ui": false,
  "parsed_task": {...},
  "existing_events": null,
  "suggested_slots": null,
  "query_events": [
    {"summary": "Laundry", "start": "2025-02-15T14:00:00", "account": "personal"}
  ]
}
```

### POST /book

Create a calendar event.

**Request:**
```json
{
  "title": "Gym",
  "date": "2025-02-21",
  "start_time": "11:00",
  "end_time": "12:00",
  "account_id": "personal",
  "category": "floating"
}
```

**Response (success):**
```json
{
  "ok": true,
  "event_link": "https://www.google.com/calendar/event?eid=...",
  "message": "Event created successfully."
}
```

**Response (error):**
```json
{
  "ok": false,
  "event_link": null,
  "message": "Error message from backend"
}
```
