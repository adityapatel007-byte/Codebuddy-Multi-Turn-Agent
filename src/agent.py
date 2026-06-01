"""
Multi-Turn Conversational Agent

Core agent class that handles conversation flow with OpenAI's GPT-4o,
maintains context across turns, and streams responses.
"""

from openai import OpenAI
from typing import Generator

from src.config import OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS
from src.memory import ConversationMemory
from src.prompts import SYSTEM_PROMPT


class CodingAgent:
    """A multi-turn coding assistant powered by GPT-4o."""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.memory = ConversationMemory(model=self.model)

    def chat(self, user_message: str) -> str:
        """Send a message and get a complete response."""
        self.memory.add_message("user", user_message)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.memory.get_messages(SYSTEM_PROMPT),
            max_tokens=MAX_TOKENS,
            temperature=0.7,
        )

        assistant_message = response.choices[0].message.content
        self.memory.add_message("assistant", assistant_message)

        return assistant_message

    def chat_stream(self, user_message: str) -> Generator[str, None, None]:
        """Send a message and stream the response token by token."""
        self.memory.add_message("user", user_message)

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=self.memory.get_messages(SYSTEM_PROMPT),
            max_tokens=MAX_TOKENS,
            temperature=0.7,
            stream=True,
        )

        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                token = chunk.choices[0].delta.content
                full_response += token
                yield token

        self.memory.add_message("assistant", full_response)

    def reset(self) -> None:
        """Reset the conversation history."""
        self.memory.clear()

    def get_stats(self) -> str:
        """Return conversation statistics."""
        return self.memory.get_summary()
