"""
CodeBuddy - Multi-Turn Coding Assistant
Streamlit UI with streaming responses, conversation memory, tool execution,
RAG, and persistent chat history.
"""

import streamlit as st
from src.agent import CodingAgent
from src.prompts import WELCOME_MESSAGE


st.set_page_config(
    page_title="CodeBuddy | AI Coding Assistant",
    page_icon="\U0001f4bb",
    layout="centered",
)

st.markdown("""
<style>
    .stChatMessage [data-testid="stMarkdownContainer"] pre {
        background-color: #1e1e1e;
        border-radius: 8px;
        padding: 12px;
    }
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

st.title("\U0001f4bb CodeBuddy")
st.caption("Your AI-powered coding assistant")


if "agent" not in st.session_state:
    st.session_state.agent = CodingAgent()
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME_MESSAGE}
    ]
    st.session_state.indexed_filenames = set()


def render_tool_calls(tool_calls):
    for tc in tool_calls:
        name = tc["name"]
        args = tc["arguments"]
        result = tc["result"]
        status = result.get("status", "unknown")

        if status == "success":
            icon = "\u2705"
        elif status == "timeout":
            icon = "\u23f1\ufe0f"
        else:
            icon = "\u274c"

        if name == "run_python":
            code = args.get("code", "")
            user_inputs = args.get("user_inputs", [])
            with st.expander(f"{icon} Executed Python Code", expanded=True):
                st.code(code, language="python")
                if user_inputs:
                    st.markdown("**User Inputs:**")
                    for i, inp in enumerate(user_inputs, 1):
                        st.markdown(f"  `input({i})` \u2192 `{inp}`")
                if result.get("output"):
                    st.markdown("**Output:**")
                    st.code(result["output"], language="text")
                if result.get("error"):
                    st.markdown("**Error:**")
                    st.code(result["error"], language="text")

        elif name == "analyze_error":
            with st.expander("\U0001f50d Error Analysis", expanded=True):
                if result.get("error_type"):
                    st.markdown(f"**Type:** `{result['error_type']}`")
                if result.get("error_message"):
                    st.markdown(f"**Message:** {result['error_message']}")
                if result.get("line_number"):
                    st.markdown(f"**Line:** {result['line_number']}")


def load_session_messages(session_id):
    db_messages = st.session_state.agent.db.get_messages(session_id)
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME_MESSAGE}
    ]
    for msg in db_messages:
        if msg["role"] in ("user", "assistant"):
            st.session_state.messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })


with st.sidebar:
    if st.button("\u2795 New Chat", use_container_width=True, type="primary"):
        st.session_state.agent.new_session()
        st.session_state.messages = [
            {"role": "assistant", "content": WELCOME_MESSAGE}
        ]
        st.session_state.indexed_filenames = set()
        st.rerun()

    st.divider()
    st.markdown("**\U0001f4ac Chat History**")

    sessions = st.session_state.agent.list_sessions(limit=15)
    current_session_id = st.session_state.agent.session_id

    if sessions:
        for session in sessions:
            sid = session["id"]
            title = session["title"]
            is_current = sid == current_session_id

            col1, col2 = st.columns([5, 1])
            with col1:
                marker = "\u25b6 " if is_current else ""
                label = f"{marker}{title}"
                if st.button(label, key=f"session_{sid}", use_container_width=True,
                           disabled=is_current):
                    st.session_state.agent.switch_session(sid)
                    load_session_messages(sid)
                    st.session_state.indexed_filenames = set()
                    st.rerun()
            with col2:
                if not is_current:
                    if st.button("\U0001f5d1", key=f"del_{sid}"):
                        st.session_state.agent.delete_session(sid)
                        st.rerun()
    else:
        st.caption("No past conversations yet")

    st.divider()
    st.markdown("**\U0001f4c1 Upload Files for Context**")
    st.caption("Upload code or docs for RAG")

    uploaded_files = st.file_uploader(
        "Drop files here",
        type=["py", "js", "ts", "jsx", "tsx", "java", "cpp", "c", "go", "rs",
              "md", "txt", "csv", "json", "yaml", "pdf"],
        accept_multiple_files=True,
        key="file_uploader",
        label_visibility="collapsed",
    )

    if uploaded_files:
        new_files = [f for f in uploaded_files if f.name not in st.session_state.indexed_filenames]
        if new_files:
            with st.spinner(f"Indexing {len(new_files)} file(s)..."):
                for f in new_files:
                    content = f.read()
                    st.session_state.agent.index_file(f.name, content)
                    st.session_state.indexed_filenames.add(f.name)
                    f.seek(0)
            st.success(f"Indexed {len(new_files)} new file(s)!")

    rag_stats = st.session_state.agent.get_rag_stats()
    if rag_stats["files_indexed"] > 0:
        st.markdown(f"**Indexed:** {rag_stats['total_chunks']} chunks from {rag_stats['files_indexed']} file(s)")
        for fname in rag_stats["filenames"]:
            st.markdown(f'<span class="file-chip">{fname}</span>', unsafe_allow_html=True)
        if st.button("\U0001f5d1 Clear Indexed Files", use_container_width=True):
            st.session_state.agent.clear_rag()
            st.session_state.indexed_filenames = set()
            st.rerun()

    st.divider()
    st.markdown("**Conversation Stats**")
    st.markdown(f"```{st.session_state.agent.get_stats()}```")

    st.divider()
    st.markdown("**Quick Prompts**")
    examples = [
        "Write and run a function to check if a number is prime",
        "Debug this code: def fib(n): return fib(n-1) + fib(n-2)",
        "Run a script that prints the first 10 Fibonacci numbers",
    ]
    for example in examples:
        if st.button(example, use_container_width=True):
            st.session_state.pending_prompt = example
            st.rerun()


for msg in st.session_state.messages:
    if msg["role"] == "tool_calls":
        with st.chat_message("assistant"):
            render_tool_calls(msg["content"])
    else:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


prompt = st.chat_input("Ask me anything about code...")

if "pending_prompt" in st.session_state:
    prompt = st.session_state.pending_prompt
    del st.session_state.pending_prompt

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("\U0001f527 Thinking..."):
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
