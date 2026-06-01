import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
MAX_CONVERSATION_TURNS = int(os.getenv("MAX_CONVERSATION_TURNS", "50"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found. Copy .env.example to .env and add your key.")
