"""
Backward-compatible entry point.
The graph definition now lives in graph.py; this module re-exports
`app` so existing imports (streamlit.py, api/main.py) keep working.
"""

from graph import app  # noqa: F401

if __name__ == "__main__":
    app.invoke({"user_input": input("\nHow can I help with your calendar? ")})
