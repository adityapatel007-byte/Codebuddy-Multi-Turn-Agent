# CodeBuddy — AI-Powered Coding Assistant

A production-grade multi-turn coding assistant built with OpenAI GPT-4o. CodeBuddy doesn't just generate code — it executes it, searches your uploaded files, remembers your conversations, and explains everything along the way.

**Live Demo:** [codebuddyv-1.streamlit.app](https://codebuddyv-1.streamlit.app)

---

## Features

### Core
- **Multi-turn conversations** with token-aware memory management (auto-truncation to stay within context limits)
- **Streaming responses** — real-time token-by-token output
- **Safety boundaries** — refuses non-coding queries, blocks malicious code generation, admits uncertainty instead of hallucinating

### Function Calling & Code Execution
- **Sandboxed Python execution** via subprocess with 10-second timeout
- **Auto-print expressions** — bare variables/dicts display output like a Python REPL
- **User input support** — code with `input()` calls runs with pre-supplied values
- **Error analysis tool** — structured traceback parsing with error type, line number, and message

### RAG (Retrieval-Augmented Generation)
- **Upload code & docs** — supports `.py`, `.js`, `.ts`, `.md`, `.txt`, `.pdf`, and 10+ more formats
- **Semantic search** — chunks files, generates embeddings via `text-embedding-3-small`, finds relevant context using cosine similarity
- **Context injection** — retrieved chunks are fed into the system prompt so answers reference your actual code
- **Source citation** — responses cite the filename they're referencing

### Persistence
- **SQLite chat history** — conversations survive page refreshes
- **Session management** — create, switch, and delete chat sessions from the sidebar
- **Auto-titling** — sessions are named from the first message

### UI
- **Custom dark theme** — deep indigo/purple palette with branded `</>` logo
- **Clean sidebar** — compact history list, monospaced stats bar
- **Inline file upload** — attach files directly above the chat input
- **Expandable tool results** — code execution output shown in collapsible panels

---

## Architecture

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────┐
│                  Streamlit UI                    │
│  (app.py — chat, file upload, session mgmt)     │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│               CodingAgent                        │
│  (src/agent.py — orchestrator)                   │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  Memory   │  │   RAG    │  │   Database    │  │
│  │ (token    │  │ (chunk → │  │  (SQLite      │  │
│  │  aware)   │  │  embed → │  │   sessions +  │  │
│  │          │  │  search) │  │   messages)   │  │
│  └──────────┘  └──────────┘  └───────────────┘  │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │            Tool Executor                  │    │
│  │  run_python()  |  analyze_error()         │    │
│  │  (subprocess)  |  (traceback parser)      │    │
│  └──────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
              OpenAI GPT-4o API
         (chat completions + embeddings)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | OpenAI GPT-4o |
| Embeddings | text-embedding-3-small |
| Frontend | Streamlit |
| Memory | In-memory with tiktoken-based truncation |
| Vector Search | NumPy cosine similarity |
| Persistence | SQLite |
| PDF Parsing | PyPDF2 |
| Deployment | Streamlit Cloud / Docker |

---

## Project Structure

```
├── app.py                  # Streamlit UI — chat, upload, sessions
├── src/
│   ├── agent.py            # Core agent — orchestrates all components
│   ├── memory.py           # Token-aware conversation memory
│   ├── rag.py              # RAG engine — parse, chunk, embed, search
│   ├── database.py         # SQLite persistence layer
│   ├── tools.py            # Function calling — code execution + error analysis
│   ├── prompts.py          # System prompts and templates
│   └── config.py           # Environment configuration
├── tests/
│   └── test_agent.py       # Unit tests
├── .streamlit/config.toml  # Custom dark theme
├── .env.example            # Environment variable template
├── Dockerfile              # Container deployment
├── requirements.txt        # Dependencies
└── README.md
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/adityapatel007-byte/Codebuddy-Multi-Turn-Agent.git
cd Codebuddy-Multi-Turn-Agent

# Setup
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your OpenAI API key to .env

# Run
streamlit run app.py
```

## Docker

```bash
docker build -t codebuddy .
docker run -p 8501:8501 --env-file .env codebuddy
```

---

## Key Concepts Demonstrated

This project showcases production-level LLM engineering skills:

- **Multi-turn context management** — sliding window memory with token budgeting via tiktoken
- **OpenAI Function Calling** — tool schemas, execution loop, result feeding
- **RAG pipeline** — document parsing, chunking, embedding, cosine similarity search
- **Sandboxed code execution** — subprocess isolation, timeout handling, input override
- **Prompt engineering** — structured system prompts with boundaries, guidelines, and RAG context injection
- **Persistence** — SQLite with session management, auto-titling, message CRUD
- **Production patterns** — environment config, Docker, `.gitignore`, error handling, clean architecture

---

## License

MIT
