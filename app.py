from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from datetime import datetime, timedelta

from parser import parse_note
from tools import fetch_calendar_events, create_calendar_event, search_calendar

class AgentState(TypedDict):
    user_input: str
    parsed_task: dict
    existing_events: List[dict]
    final_decision: str
    needs_booking_ui: bool # Add this

# --- NODES ---

def parser_node(state: AgentState):
    print("\n--- [Node: Parser] ---")
    task_object = parse_note(state["user_input"])
    return {"parsed_task": task_object.model_dump()}

def query_node(state: AgentState):
    print("--- [Node: Query Calendar] ---")
    task = state["parsed_task"]
    history = search_calendar(["work", "personal"], task['title'])
    
    if history:
        now_str = datetime.now().isoformat()
        future_events = [e for e in history if e['start'] >= now_str]
        past_events = [e for e in history if e['start'] < now_str]

        if future_events:
            next_ev = future_events[0]
            decision = f"🗓️ Scheduled: '{next_ev['summary']}' on {next_ev['start'].split('T')[0]} at {next_ev['start'].split('T')[1][:5]} ({next_ev['account']})."
        else:
            latest_past = past_events[-1]
            decision = f"✅ Not currently scheduled. Last occurrence: {latest_past['start'].split('T')[0]} ({latest_past['account']})."
    else:
        decision = f"❌ No events found for '{task['title']}'."
    return {"final_decision": decision}

def fetcher_node(state: AgentState):
    print("--- [Node: Fetcher] ---")
    target_date = state["parsed_task"]["date"] 
    events = fetch_calendar_events(["work", "personal"], target_date)
    return {"existing_events": events}

def resolver_node(state: AgentState):
    print("--- [Node: Smart Resolver] ---")
    task = state["parsed_task"]
    events = state["existing_events"]
    task_date = task["date"]
    
    # 1. Parse Busy Slots
    busy_slots = []
    for e in events:
        start_raw = e["start"].replace('Z', '').split('-08:00')[0]
        end_raw = e.get("end", start_raw).replace('Z', '').split('-08:00')[0] 
        try:
            busy_slots.append((datetime.fromisoformat(start_raw), datetime.fromisoformat(end_raw)))
        except: continue
    busy_slots.sort()

    # 2. Build the Report
    report = f"🗓️ Schedule for {task_date}:\n"
    
    if busy_slots:
        report += "\n🚫 OCCUPIED BLOCKS:\n"
        for s, e in busy_slots:
            report += f" • {s.strftime('%I:%M %p')} - {e.strftime('%I:%M %p')}\n"
    else:
        report += "\n✅ Your day is completely wide open!"

    # 3. Calculate Availability (The Inverse)
    day_start = datetime.strptime(f"{task_date} 09:00", "%Y-%m-%d %H:%M")
    day_end = datetime.strptime(f"{task_date} 19:00", "%Y-%m-%d %H:%M")
    
    available_blocks = []
    curr = day_start
    for b_s, b_e in busy_slots:
        if b_s > curr:
            available_blocks.append(f"{curr.strftime('%I:%M %p')} - {b_s.strftime('%I:%M %p')}")
        curr = max(curr, b_e)
    if curr < day_end:
        available_blocks.append(f"{curr.strftime('%I:%M %p')} - {day_end.strftime('%I:%M %p')}")

    if available_blocks:
        report += "\n🟢 BEST TIMES TO SCHEDULE:\n"
        report += "\n".join([f" • {block}" for block in available_blocks])

    return {"final_decision": report}

def summarizer_node(state: AgentState):
    print("--- [Node: Daily Briefing] ---")
    events = state["existing_events"]
    target_date = state["parsed_task"]["date"]
    
    if not events:
        return {"final_decision": f"Your calendar is clear for {target_date}."}

    report = f"📅 Agenda for {target_date}:\n" + "-"*30 + "\n"
    for acc in ["work", "personal"]:
        acc_events = [e for e in events if e['account'] == acc]
        if acc_events:
            report += f"\n{acc.upper()} ACCOUNT:\n"
            for e in acc_events:
                time = e['start'].split('T')[1][:5] if 'T' in e['start'] else "All Day"
                report += f" • {time}: {e['summary']}\n"
    return {"final_decision": report}

# def writer_node(state: AgentState):
#     print("--- [Node: Output/Writer] ---")
#     print(f"\nREPORT:\n{state['final_decision']}")
    
#     if state["parsed_task"].get("intent") in ["query", "summarize"]:
#         return state

#     time_choice = input("\nStart time? (HH:MM or 'n'): ")
#     if time_choice.lower() == 'n': return state
        
#     acc_choice = input("Account? (1=Personal, 2=Work): ")
#     target_acc = "personal" if acc_choice == "1" else "work"
    
#     if input(f"Confirm adding to {target_acc}? (y/n): ").lower() == 'y':
#         link = create_calendar_event(target_acc, state['parsed_task']['title'], f"{state['parsed_task']['date']} {time_choice}")
#         print(f"✅ Success: {link}")
#     return state
def writer_node(state: AgentState):
    print("--- [Node: Output/Writer] ---")
    
    # Check if we should even offer a booking UI
    intent = state["parsed_task"].get("intent")
    should_book = intent == "create"
    
    return {
        "final_decision": state['final_decision'],
        "needs_booking_ui": should_book
    }

# --- ROUTING LOGIC ---

def route_intent(state: AgentState):
    intent = state["parsed_task"].get("intent")
    if intent == "summarize": return "fetch"
    return "query" if intent == "query" else "fetch"

def route_after_fetch(state: AgentState):
    if state["parsed_task"].get("intent") == "summarize":
        return "summarize"
    return "resolve"

# --- GRAPH CONSTRUCTION ---

builder = StateGraph(AgentState)
builder.add_node("parse", parser_node)
builder.add_node("query", query_node)
builder.add_node("fetch", fetcher_node)
builder.add_node("resolve", resolver_node)
builder.add_node("summarize", summarizer_node)
builder.add_node("write", writer_node)

builder.set_entry_point("parse")

builder.add_conditional_edges("parse", route_intent, {"query": "query", "fetch": "fetch"})
builder.add_conditional_edges("fetch", route_after_fetch, {"summarize": "summarize", "resolve": "resolve"})

builder.add_edge("query", "write")
builder.add_edge("summarize", "write")
builder.add_edge("resolve", "write")
builder.add_edge("write", END)

app = builder.compile()
# Assuming 'app' is your compiled workflow
try:
    # 1. Get the binary PNG data
    png_binary = app.get_graph().draw_mermaid_png()
    
    # 2. Save it as a real file in your 'To-do sync' folder
    with open("my_workflow_graph.png", "wb") as f:
        f.write(png_binary)
        
    print("✅ Success! Open 'my_workflow_graph.png' in your folder to see the graph.")
except Exception as e:
    print(f"Error rendering: {e}")
if __name__ == "__main__":
    app.invoke({"user_input": input("\nHow can I help with your calendar? ")})
