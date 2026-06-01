"""
CodeBuddy — Multi-Turn Coding Assistant
Streamlit UI with streaming responses and conversation memory.
"""

import streamlit as st
from src.agent import CodingAgent
from src.prompts import WELCOME_MESSAGE


# --- Page Config ---
st.set_page_config(
    page_title="CodeBuddy | AI Coding Assistant",
    page_icon="💻",
    layout="centered",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .stChatMessage [data-testid="stMarkdownContainer"] pre {
        background-color: #1e1e1e;
        border-radius: 8px;
        padding: 12px;
    }
    .stats-bar {
        font-size: 0.8em;
        color: #888;
        padding: 4px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- Title ---
st.title("💻 CodeBuddy")
st.caption("Your AI-powered coding assistant — write, debug, and understand code")


# --- Session State ---
if "agent" not in st.session_state:
    st.session_state.agent = CodingAgent()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME_MESSAGE}
    ]


# --- Sidebar ---
with st.sidebar:
    st.header("Settings")

    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.agent.reset()
        st.session_state.messages = [
            {"role": "assistant", "content": WELCOME_MESSAGE}
        ]
        st.rerun()

    st.divider()
    st.markdown("**Conversation Stats**")
    st.markdown(f"```{st.session_state.agent.get_stats()}```")

    st.divider()
    st.markdown("**Quick Prompts**")
    examples = [
        "Write a Python function to merge two sorted lists",
        "Debug this code: def fib(n): return fib(n-1) + fib(n-2)",
        "Explain how Python decorators work with an example",
    ]
    for example in examples:
        if st.button(example, use_container_width=True):
            st.session_state.pending_prompt = example
            st.rerun()


# --- Display Chat History ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# --- Handle Input ---
prompt = st.chat_input("Ask me anything about code...")

# Check for pending prompt from sidebar
if "pending_prompt" in st.session_state:
    prompt = st.session_state.pending_prompt
    del st.session_state.pending_prompt

if prompt:
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Stream assistant response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        for token in st.session_state.agent.chat_stream(prompt):
            full_response += token
            response_placeholder.markdown(full_response + "▌")

        response_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()
