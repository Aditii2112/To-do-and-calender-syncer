import os
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

load_dotenv()

# LLM selection: Groq (free, high limit) > Ollama (local) > Gemini (free tier)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
USE_OLLAMA = os.getenv("USE_LOCAL_LLM", "").lower() in ("1", "true", "yes") or bool(os.getenv("OLLAMA_MODEL"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # or llama3-8b-8192 for faster
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()

if not GROQ_API_KEY and not USE_OLLAMA and not GOOGLE_API_KEY:
    print("Warning: No LLM configured. Set GROQ_API_KEY (free), USE_LOCAL_LLM=true (Ollama), or GOOGLE_API_KEY (Gemini).")


class Task(BaseModel):
    title: str = Field(description="Name of the task or search query")
    date: str = Field(description="Date in YYYY-MM-DD format")
    start_time: Optional[str] = Field(
        description="Start time in HH:MM (24h) if mentioned, else None"
    )
    end_time: Optional[str] = Field(
        description="End time in HH:MM (24h). If not mentioned but start exists, assume +1 hour."
    )
    category: str = Field(
        description="'fixed' for meetings/appointments, 'floating' for chores/tasks without a strict time"
    )
    account_id: str = Field(description="Must be either 'personal' or 'work'")
    intent: str = Field(
        description=(
            "'create' for adding tasks, "
            "'query' for asking about past or future events / people, or "
            "'summarize' for a briefing / agenda / list of events"
        )
    )
    summary_horizon: Optional[str] = Field(
        default="daily",
        description=(
            "Only relevant when intent='summarize'. "
            "'daily' for today / a single day, "
            "'weekly' for this week, "
            "'monthly' for this month, "
            "'yearly' for this year."
        ),
    )


def _force_query_if_obvious(user_input: str, task: Task) -> Task:
    """
    If the user is clearly asking about the past (e.g. "when did I last meet Prof Lee?"),
    force intent to 'query' so the graph runs the query node, not resolve. Helps when
    the local LLM mis-parses.
    """
    text = user_input.lower().strip()
    cleaned = user_input.strip().rstrip("?.")
    query_prefixes = (
        "when did i last meet ",
        "when did i meet ",
        "when did we meet ",
        "did i meet ",
        "when was the last time i met ",
        "when was my last meeting with ",
        "when was the last meeting with ",
        "when was my last meet with ",
        "when am i meeting ",
        "when am i seeing ",
        "when do i meet ",
        "when is my meeting with ",
        "when did i last ",
        "when was the last time ",
    )
    for prefix in query_prefixes:
        if text.startswith(prefix):
            task.intent = "query"
            rest = user_input[len(prefix):].strip().rstrip("?.")
            if rest and len(rest) < 80:
                task.title = rest
            return task
    meeting_markers = (
        "meeting with ",
        "meet with ",
        "meet ",
        "seeing ",
    )
    for marker in meeting_markers:
        pos = text.find(marker)
        if pos != -1:
            rest = cleaned[pos + len(marker):].strip()
            if rest:
                task.intent = "query"
                task.title = rest
                return task
    if any(p in text for p in ("when did i last meet", "when did i meet", "last time i ", "when did we meet", "did i meet ")):
        task.intent = "query"
    return task


def _normalize_query_title(title: str) -> str:
    """Strip trailing filler so search gets only the person/event name (e.g. 'Prof Lee')."""
    if not title:
        return title
    t = title.strip().rstrip("?.")
    for suffix in (
        " for the last time",
        " for the last time?",
        " last time",
        " last time?",
        " the last time",
        " the last time?",
    ):
        if t.lower().endswith(suffix):
            t = t[: -len(suffix)].strip().rstrip("?.,")
            break
    return t if t else title


def _force_create_if_obvious(user_input: str, task: Task) -> Task:
    """
    If the user clearly wants to add/schedule something (e.g. "add a coffee chat
    tomorrow", "schedule gym on Monday", "can you also add X"), force intent to
    'create' so the graph asks "floating or assign a time?" instead of falling
    through to fetch → resolve.
    """
    if task.intent == "query" or task.intent == "create":
        return task
    text = user_input.lower().strip()
    create_signals = (
        "add a ", "add the ", "add my ", "add ",
        "schedule a ", "schedule my ", "schedule ",
        "book a ", "book my ", "book ",
        "create a ", "create the ", "create ",
        "put a ", "put the ", "put ",
        "can you add ", "can you also add ", "can you schedule ",
        "could you add ", "could you schedule ",
        "please add ", "please schedule ",
        "i want to add ", "i want to schedule ", "i want to book ",
        "i want to go to ",
    )
    for signal in create_signals:
        if text.startswith(signal) or f" {signal}" in f" {text}":
            task.intent = "create"
            rest = text
            for s in create_signals:
                if rest.startswith(s):
                    rest = rest[len(s):]
                    break
            rest = rest.strip().rstrip("?.!")
            # Strip trailing date phrases so title is clean
            for phrase in ("tomorrow", "today", "on monday", "on tuesday", "on wednesday",
                           "on thursday", "on friday", "on saturday", "on sunday"):
                rest = rest.replace(phrase, "").strip()
            if rest:
                task.title = rest
            return task
    return task


def _force_floating_for_chores(user_input: str, task: Task) -> Task:
    """
    If the user says "add the laundry tomorrow" or similar (chore, no fixed time),
    force intent to 'create' and category to 'floating' so the task appears in
    the floating task list instead of the booking/schedule flow.
    """
    text = user_input.lower().strip()
    chore_words = ("laundry", "gym", "grocery", "groceries", "cleaning", "dishes", "cooking", "errands")
    has_chore = any(w in text for w in chore_words)
    add_phrases = ("add ", "do ", "schedule ", "put ", "create ")
    has_add = any(text.startswith(p) for p in add_phrases) or "tomorrow" in text or "today" in text

    if has_chore and has_add:
        task.intent = "create"
        task.category = "floating"
        for w in chore_words:
            if w in text:
                task.title = w
                break
    return task


def _force_summarize_if_obvious(user_input: str, task: Task) -> Task:
    """
    If the user clearly asked for a summary (e.g. "summarize my week"), force
    intent and horizon so the graph goes to summarize, not resolve. Helps when
    the local LLM mis-parses.
    """
    text = user_input.lower().strip()
    if "summarize my week" in text or ("my week" in text and "summar" in text) or "summary of my week" in text:
        task.intent = "summarize"
        task.summary_horizon = "weekly"
        return task
    if "next week" in text and ("look" in text or "summar" in text or "what" in text or "how" in text):
        task.intent = "summarize"
        task.summary_horizon = "weekly"
        return task
    if "summarize my month" in text or "summarize the month" in text or ("the month" in text and "summar" in text) or ("my month" in text and "summar" in text):
        task.intent = "summarize"
        task.summary_horizon = "monthly"
        return task
    if "summarize my year" in text or "summarize the year" in text or ("the year" in text and "summar" in text) or ("my year" in text and "summar" in text):
        task.intent = "summarize"
        task.summary_horizon = "yearly"
        return task
    if "what does my day look" in text or "what's my day" in text or "my day look like" in text:
        task.intent = "summarize"
        task.summary_horizon = "daily"
        return task
    return task


def _force_week_anchor(user_input: str, task: Task, now: datetime) -> Task:
    """
    For weekly (and monthly/yearly) summaries, pin the anchor date so we show
    the right range: 'this week' / 'summarize my week' → today (current week);
    'next week' → a day in next week.
    """
    horizon = task.summary_horizon or ""
    text = user_input.lower().strip()
    if horizon == "weekly":
        if "next week" in text:
            task.date = (now + timedelta(days=7)).strftime("%Y-%m-%d")
        else:
            task.date = now.strftime("%Y-%m-%d")
        return task
    if horizon == "monthly":
        if "next month" in text:
            # First day of next month
            next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
            task.date = next_month.strftime("%Y-%m-%d")
        else:
            task.date = now.strftime("%Y-%m-%d")
        return task
    if horizon == "yearly":
        if "next year" in text:
            task.date = now.replace(year=now.year + 1).strftime("%Y-%m-%d")
        else:
            task.date = now.strftime("%Y-%m-%d")
        return task
    return task


def _force_tomorrow_today_if_obvious(user_input: str, task: Task, now: datetime) -> Task:
    """
    When the user says 'tomorrow', 'today', or 'my day' (e.g. what does my day look like),
    set the date to actual tomorrow or today instead of trusting the LLM.
    """
    text = user_input.lower().strip()
    if "tomorrow" in text:
        task.date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    elif "today" in text and "tomorrow" not in text:
        task.date = now.strftime("%Y-%m-%d")
    elif ("my day" in text or "what does my day" in text) and "tomorrow" not in text:
        # "What does my day look like?" = today, but NOT if they said "on Tuesday" etc.
        weekdays = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
        if not any(d in text for d in weekdays):
            task.date = now.strftime("%Y-%m-%d")
    return task


def _maybe_correct_weekday(user_input: str, task: Task, now: datetime) -> Task:
    """
    If the user explicitly says a weekday (e.g. 'Tuesday') but the parsed
    date lands on a different weekday, correct it to the next occurrence
    of that weekday. Applies to both 'create' and 'summarize' (e.g. "my day on tuesday").
    """
    if task.intent not in ("create", "summarize"):
        return task

    text = user_input.lower()
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    mentioned_day = None
    for name, idx in weekdays.items():
        if name in text:
            mentioned_day = idx
    if mentioned_day is None:
        return task

    try:
        parsed_date = datetime.strptime(task.date, "%Y-%m-%d").date()
    except Exception:
        return task

    if parsed_date.weekday() == mentioned_day:
        return task

    today = now.date()
    days_ahead = (mentioned_day - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    corrected = today + timedelta(days=days_ahead)
    task.date = corrected.strftime("%Y-%m-%d")
    return task


def _get_llm():
    """Prefer Groq (free, high limit) for ~100 users; else Ollama (local); else Gemini."""
    if GROQ_API_KEY:
        from langchain_groq import ChatGroq
        return ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0)
    if USE_OLLAMA:
        from langchain_ollama import ChatOllama
        return ChatOllama(model=OLLAMA_MODEL, temperature=0)
    if GOOGLE_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", api_key=GOOGLE_API_KEY, temperature=0)
    raise RuntimeError(
        "No LLM configured. Set GROQ_API_KEY (free, ~14k req/day), "
        "USE_LOCAL_LLM=true (Ollama), or GOOGLE_API_KEY (Gemini)."
    )


def parse_note(user_input: str) -> Task:
    llm = _get_llm()
    structured_llm = llm.with_structured_output(Task)

    now = datetime.now()
    current_date_str = now.strftime("%A, %b %d, %Y")

    system_prompt = f"""Today is {current_date_str}.

You are a scheduling assistant. Output ONLY intent and date/time; we normalize the rest in code.

INTENT (exactly one):
- 'query': User asks when they met someone, or past/future events (e.g. "when did I meet Prof Lee", "when was my last meeting with X").
- 'create': User wants to add or schedule something (e.g. "add gym tomorrow", "schedule coffee chat").
- 'summarize': User wants a briefing or agenda (e.g. "what does my day look like", "summarize my week").

DATE: Use YYYY-MM-DD. If user says "tomorrow" use tomorrow's date; "today" use today; "next week" use a date in next week; "this week" use today. If unclear, use today.

TITLE: For query use only the person or event name (e.g. "Prof Lee"), not the full question. For create use the task name (e.g. "gym", "coffee chat"). For summarize use "day" or "week" etc.

CATEGORY: Use 'fixed' for meetings/appointments, 'floating' for chores. We ask the user to choose for create.
ACCOUNT_ID: 'work' or 'personal' by context.
SUMMARY_HORIZON: Only for summarize — 'daily', 'weekly', 'monthly', or 'yearly'.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    chain = prompt | structured_llm
    task: Task = chain.invoke({"input": user_input})
    now = datetime.now()
    task = _force_query_if_obvious(user_input, task)
    task = _force_summarize_if_obvious(user_input, task)
    task = _force_week_anchor(user_input, task, now)
    task = _force_create_if_obvious(user_input, task)
    task = _force_floating_for_chores(user_input, task)
    task = _force_tomorrow_today_if_obvious(user_input, task, now)
    task = _maybe_correct_weekday(user_input, task, now)
    if task.intent == "query":
        task.title = _normalize_query_title(task.title)
    return task
