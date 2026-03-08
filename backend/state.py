from typing import TypedDict, List, Optional


class AgentState(TypedDict):
    user_input: str
    parsed_task: dict
    existing_events: List[dict]       # full events: summary, start, end, account, attendees, description
    final_decision: str
    needs_booking_ui: bool
    needs_floating_vs_fixed_choice: bool  # true when we ask "floating or assign a time?" (booking)
    suggested_slots: List[dict]
    query_events: List[dict]
    summary_horizon: Optional[str]    # "daily" | "weekly" | "monthly" | "yearly"
