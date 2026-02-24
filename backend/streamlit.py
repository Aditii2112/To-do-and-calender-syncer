import streamlit as st
from app import app
from tools import create_calendar_event # Import your existing tool
import datetime

st.set_page_config(page_title="Calendar Agent", layout="wide")

# Persistent State Management
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_result" not in st.session_state:
    st.session_state.agent_result = None

# Display History
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# User Interaction
if prompt := st.chat_input("Ask about your calendar..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("🧠 Processing Graph...", expanded=False):
            # INVOKE THE ACTUAL BACKEND
            result = app.invoke({"user_input": prompt})
            st.session_state.agent_result = result
        
        st.markdown(result["final_decision"])
        st.session_state.messages.append({"role": "assistant", "content": result["final_decision"]})

# --- THE BOOKING ACTION ---
# This block runs only if the Agent found a valid scheduling intent
if st.session_state.agent_result and st.session_state.agent_result.get("needs_booking_ui"):
    st.write("---")
    st.subheader("📅 Confirm Booking Details")
    
    c1, c2 = st.columns(2)
    with c1:
        selected_time = st.time_input("Start Time", value=datetime.time(10, 0))
    with c2:
        selected_acc = st.selectbox("Account", ["Work", "Personal"])

    if st.button("Add to Calendar Now", type="primary"):
        # PULL DATA FROM THE PERSISTENT AGENT STATE
        task = st.session_state.agent_result["parsed_task"]
        acc_key = selected_acc.lower()
        
        # FORMAT FOR TOOLS.PY: "YYYY-MM-DD HH:MM"
        time_str = f"{task['date']} {selected_time.strftime('%H:%M')}"
        
        with st.spinner("Booking in Google Calendar..."):
            try:
                # EXECUTE THE ACTUAL TOOL CALL
                calendar_link = create_calendar_event(
                    acc_key, 
                    task['title'], 
                    time_str
                )
                
                st.success("✅ Success! Event created.")
                st.markdown(f"[🔗 Open in Google Calendar]({calendar_link})")
                
                # Clear the UI so you don't book the same thing twice
                st.session_state.agent_result["needs_booking_ui"] = False
                
            except Exception as e:
                st.error(f"Booking failed: {e}")