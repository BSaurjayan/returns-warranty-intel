# demo_ui.py

import streamlit as st

from app.db.database import SessionLocal
from app.chat_coordinator import Coordinator, ConversationState



st.set_page_config(page_title="Returns & Warranty Intelligence", page_icon="🧾")

st.title("🧾 Returns & Warranty Intelligence Platform (Demo)")
st.caption("MCP-style Coordinator + Retrieval/Report/Forecast Agents")

if "chat" not in st.session_state:
    st.session_state.chat = []
if "state" not in st.session_state:
    st.session_state.state = ConversationState()

db = SessionLocal()
coord = Coordinator(db)

# Render chat history
for role, msg in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(msg)

user_input = st.chat_input("Type your message...")

if user_input:
    st.session_state.chat.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    response, new_state = coord.handle_message(user_input, st.session_state.state)
    st.session_state.state = new_state

    st.session_state.chat.append(("assistant", response))
    with st.chat_message("assistant"):
        st.markdown(response)
