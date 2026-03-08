"""
LangGraph node implementations for the Oasis OS calendar agent.
Each function receives AgentState and returns a partial state update.
"""

from collections import defaultdict
from datetime import datetime, timedelta

from parser import parse_note
from state import AgentState
from tools import (
    fetch_calendar_events,
    fetch_events_range,
    search_calendar,
    semantic_search_events,
)

# ---------------------------------------------------------------------------
# 1. PARSE
# ---------------------------------------------------------------------------

def parser_node(state: AgentState) -> dict:
    print("\n--- [Node: Parser] ---")
    task = parse_note(state["user_input"])
    return {
        "parsed_task": task.model_dump(),
        "summary_horizon": task.summary_horizon or "daily",
    }


# ---------------------------------------------------------------------------
# 2. FETCH  (enhanced: attendees + description, multi-day ranges)
# ---------------------------------------------------------------------------

def fetcher_node(state: AgentState) -> dict:
    print("--- [Node: Fetcher] ---")
    task = state["parsed_task"]
    horizon = state.get("summary_horizon", "daily")
    target_date = _normalize_date(task.get("date", ""))
    accounts = ["work", "personal"]

    if horizon == "daily" or task.get("intent") != "summarize":
        events = fetch_calendar_events(accounts, target_date)
    else:
        start, end = _horizon_range(target_date, horizon)
        events = fetch_events_range(accounts, start, end)

    return {"existing_events": events, "query_events": []}


# ---------------------------------------------------------------------------
# 3. QUERY  (semantic search across attendees + descriptions)
# ---------------------------------------------------------------------------

def query_node(state: AgentState) -> dict:
    print("--- [Node: Query Calendar] ---")
    task = state["parsed_task"]
    title = task["title"]
    user_input = (state.get("user_input") or "").lower()

    api_results = search_calendar(["work", "personal"], title)
    matches = semantic_search_events(api_results, title) if api_results else []

    now_str = datetime.now().isoformat()
    future = [e for e in matches if e["start"] >= now_str]
    past = [e for e in matches if e["start"] < now_str]
    past.sort(key=lambda e: e["start"])
    future.sort(key=lambda e: e["start"])
    # "When did I last meet" → focus on past; show last occurrence first
    asking_about_past = "last" in user_input or "when did" in user_input

    MAX_RESULTS = 8

    if asking_about_past and past:
        ev = past[-1]  # most recent past event (past is now sorted ascending)
        att = _attendee_summary(ev)
        time_part = ev["start"].split("T")[1][:5] if "T" in ev.get("start", "") else ""
        decision = (
            f"✅ Last time: '{ev['summary']}' on {ev['start'].split('T')[0]}"
            + (f" at {time_part}" if time_part else "")
            + f" ({ev['account']}){att}."
        )
        if future:
            decision += f"\n📌 You also have {len(future)} upcoming occurrence(s)."
        # Only return past events, most recent first
        ordered = list(reversed(past))[:MAX_RESULTS]
    elif future and not asking_about_past:
        ev = future[0]
        att = _attendee_summary(ev)
        decision = (
            f"🗓️ Next: '{ev['summary']}' on "
            f"{ev['start'].split('T')[0]} at {ev['start'].split('T')[1][:5]} "
            f"({ev['account']}){att}."
        )
        ordered = future[:MAX_RESULTS]
    elif past:
        ev = past[-1]
        att = _attendee_summary(ev)
        decision = (
            f"✅ Not currently scheduled. Last occurrence: "
            f"'{ev['summary']}' on {ev['start'].split('T')[0]} ({ev['account']}){att}."
        )
        ordered = list(reversed(past))[:MAX_RESULTS]  # past already sorted ascending
    else:
        decision = f"❌ No events found matching '{title}'."
        ordered = []

    return {"final_decision": decision, "query_events": ordered}


# ---------------------------------------------------------------------------
# 4. RESOLVE  (inverse availability + float/book)
# ---------------------------------------------------------------------------

def resolver_node(state: AgentState) -> dict:
    print("--- [Node: Smart Resolver] ---")
    task = state["parsed_task"]
    events = state["existing_events"]
    task_date = task["date"]
    task_title = task["title"]
    category = task.get("category", "floating")

    busy_slots = _parse_busy_slots(events)

    task_date = _normalize_date(task_date)
    day_start = datetime.strptime(f"{task_date} 09:00", "%Y-%m-%d %H:%M")
    day_end = datetime.strptime(f"{task_date} 19:00", "%Y-%m-%d %H:%M")

    report = f"🗓️ Schedule for {task_date}:\n"
    if busy_slots:
        report += "\n🚫 OCCUPIED BLOCKS:\n"
        for s, e, ev in busy_slots:
            cat_icon = "📌" if ev.get("category") == "fixed" else "🔄"
            report += f" {cat_icon} {s.strftime('%I:%M %p')} – {e.strftime('%I:%M %p')}  {ev.get('summary', '')}\n"
    else:
        report += "\n✅ Your day is completely wide open!"

    free_blocks = _free_blocks(busy_slots, day_start, day_end)
    suggested_slots = []

    if free_blocks:
        report += "\n\n🟢 AVAILABLE SLOTS:\n"
        for fs, fe in free_blocks:
            report += f" • {fs.strftime('%I:%M %p')} – {fe.strftime('%I:%M %p')}\n"
            suggested_slots.append({
                "start_time": fs.strftime("%H:%M"),
                "end_time": fe.strftime("%H:%M"),
                "account_suggestions": ["work", "personal"],
            })

    if category == "floating" and free_blocks:
        best_start, best_end = free_blocks[0]
        report += (
            f"\n💡 Best slot for '{task_title}': "
            f"{best_start.strftime('%I:%M %p')} – {best_end.strftime('%I:%M %p')} (floating)"
        )

    return {"final_decision": report, "suggested_slots": suggested_slots}


# ---------------------------------------------------------------------------
# 5. SUMMARIZE  (multi-horizon, no LLM calls)
# ---------------------------------------------------------------------------

HORIZON_EMOJI = {
    "daily": "📅",
    "weekly": "📆",
    "monthly": "🗓️",
    "yearly": "📊",
}

def summarizer_node(state: AgentState) -> dict:
    print("--- [Node: Summarizer] ---")
    events = state["existing_events"]
    horizon = state.get("summary_horizon", "daily")
    target_date = state["parsed_task"]["date"]

    if not events:
        return {
            "final_decision": f"Your calendar is clear for this {horizon} period around {target_date}.",
            "suggested_slots": [],
        }

    emoji = HORIZON_EMOJI.get(horizon, "📅")

    if horizon == "daily":
        report = _daily_summary(events, target_date, emoji)
    elif horizon == "weekly":
        report = _weekly_summary(events, emoji)
    elif horizon == "monthly":
        report = _monthly_summary(events, emoji)
    else:
        report = _yearly_summary(events, emoji)

    return {"final_decision": report, "suggested_slots": []}


# ---------------------------------------------------------------------------
# 6. WRITER  (unified output)
# ---------------------------------------------------------------------------

def writer_node(state: AgentState) -> dict:
    print("--- [Node: Output/Writer] ---")
    intent = state["parsed_task"].get("intent")
    category = state["parsed_task"].get("category", "floating")

    # For booking (create): always ask "floating or assign a time?" — no category guess.
    if intent == "create":
        decision = (
            "Got it. Is this a floating task (no set time, just a reminder) "
            "or do you want to assign a time and add it to your calendar?"
        )
        return {
            "final_decision": decision,
            "needs_booking_ui": False,
            "needs_floating_vs_fixed_choice": True,
            "suggested_slots": [],
            "query_events": state.get("query_events") or [],
            "summary_horizon": state.get("summary_horizon", "daily"),
        }

    # Booking UI (→ Google Calendar) only when user chose "assign a time" (handled via /booking/slots).
    needs_booking = intent == "create" and category == "fixed"
    decision = state["final_decision"]
    if intent == "create" and category == "floating":
        decision += "\n\n🔄 This floating task has been noted! It will appear in your UI as a reminder — no calendar event created."

    return {
        "final_decision": decision,
        "needs_booking_ui": needs_booking,
        "needs_floating_vs_fixed_choice": False,
        "suggested_slots": state.get("suggested_slots") or [],
        "query_events": state.get("query_events") or [],
        "summary_horizon": state.get("summary_horizon", "daily"),
    }


# ===================================================================
# Private helpers
# ===================================================================

def _attendee_summary(ev: dict) -> str:
    names = [
        a.get("displayName") or a.get("email", "")
        for a in (ev.get("attendees") or [])
        if not a.get("self")
    ]
    if not names:
        return ""
    return " with " + ", ".join(names[:5])


def _parse_busy_slots(events: list[dict]) -> list[tuple]:
    slots = []
    for e in events:
        start_raw = e["start"].replace("Z", "").split("-08:00")[0].split("-07:00")[0]
        end_raw = e.get("end", start_raw).replace("Z", "").split("-08:00")[0].split("-07:00")[0]
        try:
            slots.append((datetime.fromisoformat(start_raw), datetime.fromisoformat(end_raw), e))
        except Exception:
            continue
    slots.sort(key=lambda x: x[0])
    return slots


def _free_blocks(busy: list[tuple], day_start: datetime, day_end: datetime) -> list[tuple]:
    blocks = []
    curr = day_start
    for b_s, b_e, _ in busy:
        if b_s > curr:
            blocks.append((curr, b_s))
        curr = max(curr, b_e)
    if curr < day_end:
        blocks.append((curr, day_end))
    return blocks


def get_suggested_slots(date: str, events: list[dict]) -> list[dict]:
    """Compute available time slots for a date from existing events. Used when user chooses 'Assign a time'."""
    task_date = _normalize_date(date)
    day_start = datetime.strptime(f"{task_date} 09:00", "%Y-%m-%d %H:%M")
    day_end = datetime.strptime(f"{task_date} 19:00", "%Y-%m-%d %H:%M")
    busy_slots = _parse_busy_slots(events)
    free_blocks = _free_blocks(busy_slots, day_start, day_end)
    return [
        {"start_time": fs.strftime("%H:%M"), "end_time": fe.strftime("%H:%M"), "account_suggestions": ["work", "personal"]}
        for fs, fe in free_blocks
    ]


def _normalize_date(s: str) -> str:
    """Return a single YYYY-MM-DD. If s is a range (e.g. 'Mar 01, 2026 to ...') or invalid, use today."""
    if not s or " to " in s:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        datetime.strptime(s.strip(), "%Y-%m-%d")
        return s.strip()
    except ValueError:
        return datetime.now().strftime("%Y-%m-%d")


def _horizon_range(anchor: str, horizon: str) -> tuple[str, str]:
    safe = _normalize_date(anchor)
    d = datetime.strptime(safe, "%Y-%m-%d")
    if horizon == "weekly":
        start = d - timedelta(days=d.weekday())
        end = start + timedelta(days=6)
    elif horizon == "monthly":
        start = d.replace(day=1)
        next_m = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_m - timedelta(days=1)
    elif horizon == "yearly":
        start = d.replace(month=1, day=1)
        end = d.replace(month=12, day=31)
    else:
        return anchor, anchor
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _daily_summary(events: list[dict], date: str, emoji: str) -> str:
    report = f"{emoji} Agenda for {date}:\n" + "─" * 36 + "\n"
    for acc in ("work", "personal"):
        acc_events = [e for e in events if e["account"] == acc]
        if not acc_events:
            continue
        acc_icon = "💼" if acc == "work" else "🏠"
        report += f"\n{acc_icon} {acc.upper()}:\n"
        for e in acc_events:
            time = _fmt_time(e["start"])
            cat_badge = "📌" if e.get("category") == "fixed" else "🔄"
            report += f"  {cat_badge} {time}  {e['summary']}\n"
    return report


def _weekly_summary(events: list[dict], emoji: str) -> str:
    by_day: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        day = e["start"][:10]
        by_day[day].append(e)

    if not by_day:
        return f"{emoji} No events this week."

    days_sorted = sorted(by_day.keys())
    report = f"{emoji} Weekly Summary ({days_sorted[0]} → {days_sorted[-1]}):\n" + "─" * 36 + "\n"
    report += f"Total events: {len(events)}\n"

    for day in days_sorted:
        day_name = datetime.strptime(day, "%Y-%m-%d").strftime("%a %b %d")
        day_events = by_day[day]
        report += f"\n📌 {day_name} — {len(day_events)} event(s)\n"
        for e in day_events:
            time = _fmt_time(e["start"])
            report += f"   • {time}  {e['summary']}  [{e['account']}]\n"
    return report


def _monthly_summary(events: list[dict], emoji: str) -> str:
    by_week: dict[int, list[dict]] = defaultdict(list)
    for e in events:
        d = datetime.fromisoformat(e["start"][:10])
        week_num = d.isocalendar()[1]
        by_week[week_num].append(e)

    report = f"{emoji} Monthly Summary:\n" + "─" * 36 + "\n"
    report += f"Total events: {len(events)}\n"

    work_count = sum(1 for e in events if e["account"] == "work")
    personal_count = len(events) - work_count
    report += f"💼 Work: {work_count}  |  🏠 Personal: {personal_count}\n"

    for wk in sorted(by_week.keys()):
        wk_events = by_week[wk]
        report += f"\n  Week {wk}: {len(wk_events)} event(s)\n"
        for e in wk_events[:5]:
            report += f"    • {e['start'][:10]} {_fmt_time(e['start'])}  {e['summary']}\n"
        if len(wk_events) > 5:
            report += f"    … and {len(wk_events) - 5} more\n"
    return report


def _yearly_summary(events: list[dict], emoji: str) -> str:
    by_month: dict[int, list[dict]] = defaultdict(list)
    for e in events:
        month = int(e["start"][5:7])
        by_month[month].append(e)

    month_names = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]

    report = f"{emoji} Yearly Summary:\n" + "─" * 36 + "\n"
    report += f"Total events: {len(events)}\n\n"

    for m in sorted(by_month.keys()):
        m_events = by_month[m]
        work_ct = sum(1 for e in m_events if e["account"] == "work")
        pers_ct = len(m_events) - work_ct
        bar = "█" * min(len(m_events), 30)
        report += f"  {month_names[m]:>3}  {bar} {len(m_events)}  (💼{work_ct} 🏠{pers_ct})\n"

    busiest = max(by_month.items(), key=lambda x: len(x[1]))
    report += f"\nBusiest month: {month_names[busiest[0]]} ({len(busiest[1])} events)"
    return report


def _fmt_time(iso: str) -> str:
    if "T" not in iso:
        return "All Day"
    t = iso.split("T")[1][:5]
    h, m = int(t[:2]), t[3:]
    period = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m} {period}"
