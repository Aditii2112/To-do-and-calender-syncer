import datetime

import streamlit as st

from graph import app
from tools import create_calendar_event

st.set_page_config(page_title="Oasis OS — Calendar Agent", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_result" not in st.session_state:
    st.session_state.agent_result = None

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Ask about your calendar..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("🧠 Processing Graph...", expanded=False):
            result = app.invoke({"user_input": prompt})
            st.session_state.agent_result = result

        st.markdown(result["final_decision"])
        st.session_state.messages.append(
            {"role": "assistant", "content": result["final_decision"]}
        )

if st.session_state.agent_result and st.session_state.agent_result.get("needs_booking_ui"):
    st.write("---")
    st.subheader("📅 Confirm Booking Details")

    c1, c2 = st.columns(2)
    with c1:
        selected_time = st.time_input("Start Time", value=datetime.time(10, 0))
    with c2:
        selected_acc = st.selectbox("Account", ["Work", "Personal"])

    if st.button("Add to Calendar Now", type="primary"):
        task = st.session_state.agent_result["parsed_task"]
        acc_key = selected_acc.lower()
        time_str = f"{task['date']} {selected_time.strftime('%H:%M')}"

        with st.spinner("Booking in Google Calendar..."):
            try:
                calendar_link = create_calendar_event(acc_key, task["title"], time_str)
                st.success("✅ Success! Event created.")
                st.markdown(f"[🔗 Open in Google Calendar]({calendar_link})")
                st.session_state.agent_result["needs_booking_ui"] = False
            except Exception as e:
                st.error(f"Booking failed: {e}")
