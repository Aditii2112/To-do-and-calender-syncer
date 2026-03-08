"""
LangGraph workflow definition for the Oasis OS calendar agent.

Graph flow:
  parse ─→ route_intent ─┬─ "query"  → query     → write → END
                          └─ "fetch"  → fetch ─→ route_after_fetch ─┬─ "summarize" → summarize → write → END
                                                                    └─ "resolve"  → resolve   → write → END
"""

from langgraph.graph import END, StateGraph

from nodes import (
    fetcher_node,
    parser_node,
    query_node,
    resolver_node,
    summarizer_node,
    writer_node,
)
from state import AgentState


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def route_intent(state: AgentState) -> str:
    intent = state["parsed_task"].get("intent")
    if intent == "query":
        return "query"
    if intent == "create":
        # Ask "floating or assign a time?" first — no fetch/resolve until user chooses
        return "write"
    return "fetch"  # "summarize" needs fetched events


def route_after_fetch(state: AgentState) -> str:
    if state["parsed_task"].get("intent") == "summarize":
        return "summarize"
    return "resolve"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

builder = StateGraph(AgentState)

builder.add_node("parse", parser_node)
builder.add_node("query", query_node)
builder.add_node("fetch", fetcher_node)
builder.add_node("resolve", resolver_node)
builder.add_node("summarize", summarizer_node)
builder.add_node("write", writer_node)

builder.set_entry_point("parse")

builder.add_conditional_edges(
    "parse",
    route_intent,
    {"query": "query", "fetch": "fetch", "write": "write"},
)
builder.add_conditional_edges(
    "fetch",
    route_after_fetch,
    {"summarize": "summarize", "resolve": "resolve"},
)

builder.add_edge("query", "write")
builder.add_edge("summarize", "write")
builder.add_edge("resolve", "write")
builder.add_edge("write", END)

app = builder.compile()


if __name__ == "__main__":
    try:
        png_binary = app.get_graph().draw_mermaid_png()
        with open("my_workflow_graph.png", "wb") as f:
            f.write(png_binary)
        print("Graph saved to my_workflow_graph.png")
    except Exception as e:
        print(f"Error rendering: {e}")

    app.invoke({"user_input": input("\nHow can I help with your calendar? ")})
