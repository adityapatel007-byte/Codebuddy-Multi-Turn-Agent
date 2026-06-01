# CodeBuddy — Multi-Turn Conversational Coding Agent

A multi-turn AI coding assistant built with OpenAI GPT-4o and Streamlit. Supports code generation, debugging, and code explanation with full conversation memory.

## Features

- **Multi-turn conversation** with token-aware memory management
- **Streaming responses** for real-time output
- **Code generation** — describe what you need in plain English
- **Debugging** — paste buggy code, get fixes with explanations
- **Dark-themed UI** optimized for code readability

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | OpenAI GPT-4o |
| Frontend | Streamlit |
| Memory | In-memory with token-aware truncation |
| Tokenizer | tiktoken |
| Deployment | Docker |

## Quick Start

```bash
# 1. Clone and navigate
cd 01-multi-turn-conversational-agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your OpenAI API key

# 5. Run the app
streamlit run app.py
```

## Docker

```bash
docker build -t codebuddy .
docker run -p 8501:8501 --env-file .env codebuddy
```

## Project Structure

```
├── app.py              # Streamlit UI
├── src/
│   ├── agent.py        # Core agent with OpenAI integration
│   ├── memory.py       # Conversation memory with token management
│   ├── prompts.py      # System prompts and templates
│   └── config.py       # Environment configuration
├── tests/
│   └── test_agent.py   # Unit tests for memory manager
├── .env.example        # Environment variable template
├── Dockerfile          # Container deployment
└── requirements.txt    # Python dependencies
```

## Running Tests

```bash
pytest tests/ -v
```

## Architecture

```
User Input → Streamlit UI → CodingAgent → OpenAI GPT-4o
                                ↕
                        ConversationMemory
                     (token-aware truncation)
```

## Key Concepts Demonstrated

- **Multi-turn context management** — maintaining coherent conversations across many turns
- **Token budgeting** — automatic truncation to stay within model context limits
- **Streaming** — real-time token-by-token response rendering
- **Clean architecture** — separated concerns (agent, memory, prompts, config)
- **Production patterns** — environment config, Docker, testing, error handling
