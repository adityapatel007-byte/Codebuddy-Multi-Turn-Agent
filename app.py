"""
CodeBuddy — Multi-Turn Coding Assistant
Streamlit UI with streaming responses, conversation memory, tool execution, and RAG.
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
    .file-chip {
        display: inline-block;
        background: #2d6a4f;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

# --- Title ---
st.title("💻 CodeBuddy")
st.caption("Your AI-powered coding assistant — write, debug, run code, and ask about your files")


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

        if status == "success":
            icon = "✅"
        elif status == "timeout":
            icon = "⏱️"
        else:
            icon = "❌"

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
            with st.expander("🔍 Error Analysis", expanded=True):
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

    # --- File Upload (RAG) ---
    st.divider()
    st.markdown("**📁 Upload Files for Context**")
    st.caption("Upload code or docs — CodeBuddy will answer based on your files")

    uploaded_files = st.file_uploader(
        "Drop files here",
        type=["py", "js", "ts", "jsx", "tsx", "java", "cpp", "c", "go", "rs",
              "md", "txt", "csv", "json", "yaml", "pdf"],
        accept_multiple_files=True,
        key="file_uploader",
        label_visibility="collapsed",
    )

    if uploaded_files:
        # Track which files are already indexed
        if "indexed_filenames" not in st.session_state:
            st.session_state.indexed_filenames = set()

        new_files = [f for f in uploaded_files if f.name not in st.session_state.indexed_filenames]

        if new_files:
            with st.spinner(f"Indexing {len(new_files)} file(s)..."):
                for f in new_files:
                    content = f.read()
                    num_chunks = st.session_state.agent.index_file(f.name, content)
                    st.session_state.indexed_filenames.add(f.name)
                    f.seek(0)  # Reset file pointer

            st.success(f"Indexed {len(new_files)} new file(s)!")

    # Show RAG stats
    rag_stats = st.session_state.agent.get_rag_stats()
    if rag_stats["files_indexed"] > 0:
        st.markdown(f"**Indexed:** {rag_stats['total_chunks']} chunks from {rag_stats['files_indexed']} file(s)")
        for fname in rag_stats["filenames"]:
            st.markdown(f'<span class="file-chip">{fname}</span>', unsafe_allow_html=True)

        if st.button("🗑️ Clear Indexed Files", use_container_width=True):
            st.session_state.agent.clear_rag()
            st.session_state.indexed_filenames = set()
            st.rerun()

    # --- Stats ---
    st.divider()
    st.markdown("**Conversation Stats**")
    st.markdown(f"```{st.session_state.agent.get_stats()}```")

    # --- Quick Prompts ---
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
        with st.chat_message("assistant"):
            render_tool_calls(msg["content"])
    else:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


# --- Handle Input ---
prompt = st.chat_input("Ask me anything about code...")

if "pending_prompt" in st.session_state:
    prompt = st.session_state.pending_prompt
    del st.session_state.pending_prompt

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🔧 Thinking..."):
            tool_calls_data = []
            full_response = ""

            for token in st.session_state.agent.chat_stream(prompt):
                full_response += token

            tool_calls_data = st.session_state.agent.get_last_tool_calls()

    if tool_calls_data:
        st.session_state.messages.append({
            "role": "tool_calls",
            "content": tool_calls_data,
        })

    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()
