"""
CodeBuddy - Multi-Turn Coding Assistant
"""

import streamlit as st
from src.agent import CodingAgent
from src.prompts import WELCOME_MESSAGE

# --- Config ---
st.set_page_config(
    page_title="CodeBuddy",
    page_icon="</> ",
    layout="centered",
)

# --- Global CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden !important;}
    [data-testid="collapsedControl"] {visibility: visible !important; display: block !important; z-index: 999;}

    .cb-header {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 12px 0 8px 0;
    }
    .cb-logo {
        width: 40px; height: 40px;
        background: linear-gradient(135deg, #6C63FF, #4F46E5);
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 20px; color: white; font-weight: 700;
        font-family: 'SF Mono', 'Fira Code', monospace;
        flex-shrink: 0;
    }
    .cb-title { font-size: 26px; font-weight: 700; color: #e4e4e7; letter-spacing: -0.5px; line-height: 1; }
    .cb-subtitle { font-size: 13px; color: #71717a; margin-top: 2px; }

    [data-testid="stSidebar"] { padding-top: 1rem; }
    .sidebar-label {
        font-size: 11px; font-weight: 600; color: #71717a;
        text-transform: uppercase; letter-spacing: 1.2px;
        margin: 16px 0 8px 0;
    }

    .stChatMessage [data-testid="stMarkdownContainer"] pre {
        background-color: #111118 !important;
        border: 1px solid #27272a;
        border-radius: 10px; padding: 14px; font-size: 13px;
    }
    .stChatMessage [data-testid="stMarkdownContainer"] code { color: #a78bfa; }
    .stChatMessage [data-testid="stChatMessageAvatar"] { border-radius: 8px; }

    .file-chip {
        display: inline-block;
        background: rgba(108, 99, 255, 0.15); color: #a78bfa;
        padding: 3px 10px; border-radius: 20px; font-size: 12px;
        margin: 2px; border: 1px solid rgba(108, 99, 255, 0.2);
    }
    .stats-bar {
        background: #111118; border: 1px solid #27272a;
        border-radius: 8px; padding: 8px 12px;
        font-family: 'SF Mono', 'Fira Code', monospace;
        font-size: 11px; color: #71717a;
    }

    [data-testid="stChatInput"] textarea { border-radius: 12px !important; }

    /* Upload bar above chat input */
    .upload-bar {
        display: flex; align-items: center; gap: 8px;
        padding: 4px 0; margin-bottom: 4px;
    }
</style>
""", unsafe_allow_html=True)


# --- Custom Header ---
st.markdown("""
<div class="cb-header">
    <div class="cb-logo">&lt;/&gt;</div>
    <div>
        <div class="cb-title">CodeBuddy</div>
        <div class="cb-subtitle">AI-powered coding assistant</div>
    </div>
</div>
""", unsafe_allow_html=True)


# --- Session State ---
if "agent" not in st.session_state:
    st.session_state.agent = CodingAgent()
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME_MESSAGE}
    ]
    st.session_state.indexed_filenames = set()


# --- Helpers ---
def render_tool_calls(tool_calls):
    for tc in tool_calls:
        name = tc["name"]
        args = tc["arguments"]
        result = tc["result"]
        status = result.get("status", "unknown")

        icon = {"success": "✅", "timeout": "⏱️", "error": "❌"}.get(status, "❓")

        if name == "run_python":
            code = args.get("code", "")
            user_inputs = args.get("user_inputs", [])
            with st.expander(f"{icon} Code Execution", expanded=True):
                st.code(code, language="python")
                if user_inputs:
                    st.caption("Inputs: " + " | ".join(f"`{inp}`" for inp in user_inputs))
                if result.get("output"):
                    st.code(result["output"], language="text")
                if result.get("error"):
                    st.error(result["error"])
        elif name == "analyze_error":
            with st.expander(f"{icon} Error Analysis", expanded=True):
                parts = []
                if result.get("error_type"):
                    parts.append(f"**{result['error_type']}**")
                if result.get("error_message"):
                    parts.append(result["error_message"])
                if result.get("line_number"):
                    parts.append(f"Line {result['line_number']}")
                st.markdown(" — ".join(parts))


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


# --- Sidebar (clean: just history + stats) ---
with st.sidebar:
    if st.button("New Chat", use_container_width=True, type="primary"):
        st.session_state.agent.new_session()
        st.session_state.messages = [
            {"role": "assistant", "content": WELCOME_MESSAGE}
        ]
        st.session_state.indexed_filenames = set()
        st.rerun()

    st.markdown('<div class="sidebar-label">History</div>', unsafe_allow_html=True)
    sessions = st.session_state.agent.list_sessions(limit=10)
    current_session_id = st.session_state.agent.session_id

    if sessions:
        for session in sessions:
            sid = session["id"]
            title = session["title"]
            is_current = sid == current_session_id
            col1, col2 = st.columns([6, 1])
            with col1:
                marker = "▪ " if is_current else ""
                label = f"{marker}{title}"
                if st.button(label, key=f"s_{sid}", use_container_width=True, disabled=is_current):
                    st.session_state.agent.switch_session(sid)
                    load_session_messages(sid)
                    st.session_state.indexed_filenames = set()
                    st.rerun()
            with col2:
                if not is_current:
                    if st.button("×", key=f"d_{sid}"):
                        st.session_state.agent.delete_session(sid)
                        st.rerun()
    else:
        st.caption("No conversations yet")

    st.markdown('<div class="sidebar-label">Stats</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stats-bar">{st.session_state.agent.get_stats()}</div>', unsafe_allow_html=True)


# --- Chat Display ---
for msg in st.session_state.messages:
    if msg["role"] == "tool_calls":
        with st.chat_message("assistant", avatar="\U0001f916"):
            render_tool_calls(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message("assistant", avatar="\U0001f916"):
            st.markdown(msg["content"])
    elif msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])


# --- File Upload (in main area, above chat input) ---
with st.expander("📎 Attach files for context", expanded=False):
    uploaded_files = st.file_uploader(
        "Upload code or docs",
        type=["py", "js", "ts", "jsx", "tsx", "java", "cpp", "c", "go", "rs",
              "md", "txt", "csv", "json", "yaml", "pdf"],
        accept_multiple_files=True,
        key="file_uploader",
        label_visibility="collapsed",
    )

    if uploaded_files:
        new_files = [f for f in uploaded_files if f.name not in st.session_state.indexed_filenames]
        if new_files:
            with st.spinner(f"Indexing {len(new_files)} files..."):
                for f in new_files:
                    content = f.read()
                    st.session_state.agent.index_file(f.name, content)
                    st.session_state.indexed_filenames.add(f.name)
                    f.seek(0)

    rag_stats = st.session_state.agent.get_rag_stats()
    if rag_stats["files_indexed"] > 0:
        chips = " ".join(f'<span class="file-chip">{fn}</span>' for fn in rag_stats["filenames"])
        col_a, col_b = st.columns([5, 1])
        with col_a:
            st.markdown(chips, unsafe_allow_html=True)
        with col_b:
            if st.button("Clear", key="clear_rag"):
                st.session_state.agent.clear_rag()
                st.session_state.indexed_filenames = set()
                st.rerun()


# --- Chat Input ---
prompt = st.chat_input("What do you need help with?")

if "pending_prompt" in st.session_state:
    prompt = st.session_state.pending_prompt
    del st.session_state.pending_prompt

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="\U0001f916"):
        with st.spinner("Thinking..."):
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
