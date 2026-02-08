
# 📅 AI Calendar Intelligence Agent
A Multi-Agent Orchestrator for Intelligent Scheduling and Daily Briefings

Built with LangGraph, Google Gemini 1.5 Flash, and the Google Calendar API. This agent goes beyond simple scheduling by analyzing user intent, managing cross-account availability (Work/Personal), and providing structured daily briefings.

**System Architecture**
The agent is built as a Stateful Graph. Instead of a linear script, it uses a state machine to route tasks based on the user's natural language.

**How it Works: The Node Logic**
parser_node: Uses Gemini 1.5 Flash to transform raw text into a structured JSON task object (Identifying Intent: create, query, or summarize).

query_node: Specialized for historical searches. It looks across both Work and Personal accounts to find the last time a specific event occurred.

fetcher_node: A middleware node that retrieves all events for a target date to populate the agent's "short-term memory."

resolver_node: Calculates the Inverse Availability. Instead of just showing busy blocks, it identifies the "Smart Gaps" where you are actually free to meet.

summarizer_node: Formats a clean, distraction-free agenda for the day, separated by account.

writer_node: The final state-setter that triggers the Streamlit UI to render interactive booking widgets.

![Workflow graph](assets/my_workflow_graph.jpg)


# Features
Dual-Account Sync: Simultaneously fetches and manages data from generic Work and Personal Google Calendar accounts.

Intent-Based Routing: Automatically distinguishes between "What's my day look like?" (Summary) and "When did I last do laundry?" (Query).

Interactive Web UI: A Streamlit frontend that replaces terminal prompts with a modern chat interface and time-picker widgets.

No-AI Summarization: Optimized for performance. Once data is fetched, the briefing is generated via logic rather than extra LLM calls to save on latency.

# **🛠️ Tech Stack**

Orchestration: LangGraph (StateGraph)

LLM: Google Gemini 2.5 Flash (Free source models can also be used)

Frontend: Streamlit

API: Google Calendar REST API

Environment: Python 3.10+

# Installation & Setup
Clone the repo:

Bash
git clone https://github.com/your-username/To-do-Sync.git
cd To-do-Sync
Install Dependencies:

Bash
pip install -r requirements.txt
Google API Setup:

Enable Google Calendar API in Google Cloud Console.

Download credentials.json and place it in the root folder.

On the first run, the app will open a browser to generate token_work.json and token_personal.json.

Environment Variables: Create a .env file:

Plaintext
GOOGLE_API_KEY=your_gemini_api_key_here
🖥️ Running the App
To launch the interactive web dashboard:

Bash
streamlit run streamlit.py
🛡️ Security Note
This repository does not contain private tokens or credentials. Users must provide their own credentials.json and .env files to run the agent locally.
