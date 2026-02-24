import os
from datetime import datetime
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

import os
from dotenv import load_dotenv

# Load the variables from .env into the system environment
load_dotenv()

# Access the key safely
api_key = os.getenv("GOOGLE_API_KEY")

# Now use it in your LLM configuration
if api_key:
    os.environ["GOOGLE_API_KEY"] = api_key
else:
    print("Error: GOOGLE_API_KEY not found in .env file")

class Task(BaseModel):
    title: str = Field(description="Name of the task")
    date: str = Field(description="Date in YYYY-MM-DD format")
    start_time: Optional[str] = Field(description="Start time in HH:MM (24h) if mentioned, else None")
    end_time: Optional[str] = Field(description="End time in HH:MM (24h). If not mentioned but start exists, assume +1 hour.")
    category: str = Field(description="'fixed' for meetings/appointments, 'floating' for chores/tasks without a strict time")
    account_id: str = Field(description="Must be either 'personal' or 'work'")
    intent: str = Field(description="'create' for adding tasks, 'query' for asking about the past, or 'summarize' for a briefing, a list of events, or asking 'What's my day look like?'")

def parse_note(user_input: str):
    # Ensure you are using the correct model string for your environment
    llm = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash-lite", temperature=0)
    structured_llm = llm.with_structured_output(Task)
    
    now = datetime.now()
    current_date_str = now.strftime("%A, %b %d, %Y")
    
    system_prompt = f"""
Today is {current_date_str}. 

You are a highly efficient scheduling assistant. Your goal is to parse user intent into a structured format.

DIRECTIONS:
1. CATEGORY:
   - 'fixed': Tasks that require a specific time or involve other people (meetings, appointments, flights).
   - 'floating': Flexible tasks that can be done anytime (chores, habits, errands).

2. ACCOUNT_ID:
   - Categorize the task into 'work' or 'personal' based on the context of the input.
   - If it sounds professional, academic, or corporate, use 'work'.
   - If it sounds like home life, health, or social, use 'personal'.

3. You must strictly categorize the user's INTENT:
1. 'query': Use this ONLY if the user is asking about the PAST or Future
   - Example: "When was the last time I did laundry?", "When did I meet Sumitro?"
2. 'create': Use this if the user is seeking a suggestion for a time or scheduling a task.
   - Example: "When can I do laundry?", "Find a time for a meeting", "Schedule gym."
3. - 'summarize': If the user asks for a briefing, an agenda, or "what does my day look like".



4. DATES/TIMES:
   - Always output dates in YYYY-MM-DD.
   - If no time is mentioned for a 'fixed' task, leave start_time as None.
"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])
    
    chain = prompt | structured_llm
    return chain.invoke({"input": user_input})