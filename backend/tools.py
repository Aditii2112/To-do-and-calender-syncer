from auth import get_calendar_service
from datetime import datetime, timedelta


def fetch_calendar_events(accounts: list[str], target_date: str) -> list[dict]:
    """Fetch events for a single date, including attendees and description."""
    all_events = []
    time_min = f"{target_date}T00:00:00-08:00"
    time_max = f"{target_date}T23:59:59-08:00"

    for acc in accounts:
        try:
            service = get_calendar_service(acc)
            result = service.events().list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            for e in result.get("items", []):
                normalized = _normalize_event(e, acc)
                if _should_exclude_event(normalized):
                    continue
                all_events.append(normalized)
        except Exception as err:
            print(f"Error fetching from {acc}: {err}")

    return all_events


def fetch_events_range(accounts: list[str], start_date: str, end_date: str) -> list[dict]:
    """Fetch events across a date range for weekly/monthly/yearly summaries."""
    all_events = []
    time_min = f"{start_date}T00:00:00-08:00"
    time_max = f"{end_date}T23:59:59-08:00"

    for acc in accounts:
        try:
            service = get_calendar_service(acc)
            result = service.events().list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                maxResults=2500,
            ).execute()

            for e in result.get("items", []):
                normalized = _normalize_event(e, acc)
                if _should_exclude_event(normalized):
                    continue
                all_events.append(normalized)
        except Exception as err:
            print(f"Error fetching range from {acc}: {err}")

    return all_events


def search_calendar(accounts: list[str], query_text: str) -> list[dict]:
    """Google Calendar q-parameter search across 60 days past + 60 days future."""
    all_events = []
    start_search = (datetime.utcnow() - timedelta(days=60)).isoformat() + "Z"
    end_search = (datetime.utcnow() + timedelta(days=60)).isoformat() + "Z"

    for acc in accounts:
        try:
            service = get_calendar_service(acc)
            result = service.events().list(
                calendarId="primary",
                q=query_text,
                timeMin=start_search,
                timeMax=end_search,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            for e in result.get("items", []):
                normalized = _normalize_event(e, acc)
                if _should_exclude_event(normalized):
                    continue
                all_events.append(normalized)
        except Exception as err:
            print(f"Error searching {acc}: {err}")

    all_events.sort(key=lambda x: x["start"])
    return all_events


def semantic_search_events(events: list[dict], query: str) -> list[dict]:
    """
    In-memory semantic search over already-fetched events.
    Matches against summary, attendees, and description fields
    so queries like 'When did I meet Prof Lee?' work even if
    the name only appears in the attendee list.
    """
    query_lower = query.lower()
    tokens = query_lower.split()

    scored: list[tuple[int, dict]] = []
    for ev in events:
        score = 0
        summary = (ev.get("summary") or "").lower()
        description = (ev.get("description") or "").lower()
        attendee_blob = " ".join(
            a.get("email", "") + " " + a.get("displayName", "")
            for a in (ev.get("attendees") or [])
        ).lower()

        searchable = f"{summary} {description} {attendee_blob}"

        for token in tokens:
            if token in searchable:
                score += 1
            if token in summary:
                score += 2
            if token in attendee_blob:
                score += 2

        if score > 0:
            scored.append((score, ev))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [ev for _, ev in scored]


def create_calendar_event(
    account_name: str,
    summary: str,
    start_time_str: str,
    end_time_str: str | None = None,
    description: str = "",
    category: str = "fixed",
) -> str:
    """
    Insert an event. start_time_str format: 'YYYY-MM-DD HH:MM'.
    Returns the Google Calendar HTML link.
    """
    service = get_calendar_service(account_name)

    start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
    end_dt = (
        datetime.strptime(end_time_str, "%Y-%m-%d %H:%M")
        if end_time_str
        else start_dt + timedelta(hours=1)
    )

    color_id = "9" if category == "floating" else "1"

    event_body = {
        "summary": summary,
        "description": description,
        "colorId": color_id,
        "start": {
            "dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "America/Los_Angeles",
        },
        "end": {
            "dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "America/Los_Angeles",
        },
        "extendedProperties": {
            "private": {"oasis_category": category}
        },
    }

    event = service.events().insert(calendarId="primary", body=event_body).execute()
    return event.get("htmlLink")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_event(raw: dict, account: str) -> dict:
    """Extract a uniform dict from a raw Google Calendar event."""
    attendees_raw = raw.get("attendees") or []
    attendees = [
        {
            "email": a.get("email", ""),
            "displayName": a.get("displayName", ""),
            "self": a.get("self", False),
        }
        for a in attendees_raw
    ]

    ext_props = raw.get("extendedProperties", {}).get("private", {})
    category = ext_props.get("oasis_category", "fixed")

    return {
        "id": raw.get("id", ""),
        "summary": raw.get("summary", "(No title)"),
        "start": raw.get("start", {}).get("dateTime") or raw.get("start", {}).get("date", ""),
        "end": raw.get("end", {}).get("dateTime") or raw.get("end", {}).get("date", ""),
        "account": account,
        "attendees": attendees,
        "description": raw.get("description", ""),
        "category": category,
    }


def _should_exclude_event(event: dict) -> bool:
    """
    Legacy cleanup: older buggy versions could write floating tasks into Google
    Calendar. Those should stay UI-only, so we hide them from fetched calendar
    agendas and search results.
    """
    return event.get("category") == "floating"


def delete_calendar_event(account_name: str, event_id: str) -> None:
    """Delete an event from Google Calendar. Raises on failure."""
    if not event_id:
        raise ValueError("event_id is required")
    service = get_calendar_service(account_name)
    service.events().delete(calendarId="primary", eventId=event_id).execute()


if __name__ == "__main__":
    test_date = datetime.now().strftime("%Y-%m-%d")
    events = fetch_calendar_events(["work", "personal"], test_date)
    print(f"\n--- Events for {test_date} ---")
    for e in events:
        att_names = [a["displayName"] or a["email"] for a in e["attendees"]]
        print(f"[{e['account']}] {e['start']} - {e['summary']}  attendees={att_names}")
