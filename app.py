"""
CodeBuddy — Multi-Turn Coding Assistant
Streamlit UI with streaming responses, conversation memory, and tool execution.
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
    .tool-call-box {
        background-color: #1a1a2e;
        border-left: 3px solid #4F8BF9;
        border-radius: 4px;
        padding: 10px 14px;
        margin: 8px 0;
        font-size: 0.85em;
    }
    .tool-success { border-left-color: #00c853; }
    .tool-error { border-left-color: #ff5252; }
    .tool-timeout { border-left-color: #ffc107; }
</style>
""", unsafe_allow_html=True)

# --- Title ---
st.title("💻 CodeBuddy")
st.caption("Your AI-powered coding assistant — write, debug, and run code")


# --- Session State ---
if "agent" not in st.session_state:
    st.session_state.agent = CodingAgent()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME_MESSAGE}
    ]


# --- Helper: Render tool calls ---
def render_tool_calls(tool_calls: list[dict]):
    """Display tool execution results in the chat."""
    for tc in tool_calls:
        name = tc["name"]
        args = tc["arguments"]
        result = tc["result"]
        status = result.get("status", "unknown")

        # Status icon and CSS class
        if status == "success":
            icon, css_class = "✅", "tool-success"
        elif status == "timeout":
            icon, css_class = "⏱️", "tool-timeout"
        else:
            icon, css_class = "❌", "tool-error"

        if name == "run_python":
            code = args.get("code", "")
            user_inputs = args.get("user_inputs", [])
            with st.expander(f"{icon} Executed Python Code", expanded=True):
                st.code(code, language="python")
                if user_inputs:
                    st.markdown("**User Inputs:**")
                    for i, inp in enumerate(user_inputs, 1):
                        st.markdown(f"  `input({i})` → `{inp}`")
                if result.get("output"):
                    st.markdown("**Output:**")
                    st.code(result["output"], language="text")
                if result.get("error"):
                    st.markdown("**Error:**")
                    st.code(result["error"], language="text")

        elif name == "analyze_error":
            with st.expander(f"🔍 Error Analysis", expanded=True):
                if result.get("error_type"):
                    st.markdown(f"**Type:** `{result['error_type']}`")
                if result.get("error_message"):
                    st.markdown(f"**Message:** {result['error_message']}")
                if result.get("line_number"):
                    st.markdown(f"**Line:** {result['line_number']}")


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
        "Write and run a Python function to check if a number is prime",
        "Debug this code: def fib(n): return fib(n-1) + fib(n-2)",
        "Run a Python script that prints the first 10 Fibonacci numbers",
    ]
    for example in examples:
        if st.button(example, use_container_width=True):
            st.session_state.pending_prompt = example
            st.rerun()


# --- Display Chat History ---
for msg in st.session_state.messages:
    if msg["role"] == "tool_calls":
        # Render tool call results
        with st.chat_message("assistant"):
            render_tool_calls(msg["content"])
    else:
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

    # Show thinking spinner while tools execute
    with st.chat_message("assistant"):
        # First, check if tools will be called (show spinner)
        with st.spinner("🔧 Running tools..."):
            tool_calls_data = []
            full_response = ""

            for token in st.session_state.agent.chat_stream(prompt):
                full_response += token

            # Get tool calls that happened during this interaction
            tool_calls_data = st.session_state.agent.get_last_tool_calls()

    # Store tool calls in message history (if any)
    if tool_calls_data:
        st.session_state.messages.append({
            "role": "tool_calls",
            "content": tool_calls_data,
        })

    # Store assistant response
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()
