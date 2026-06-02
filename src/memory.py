"""
Conversation Memory Manager

Handles in-memory conversation history with token-aware truncation.
Keeps the conversation within the model's context window by summarizing
or dropping older messages when the token count exceeds the limit.
"""

import tiktoken
from typing import Optional


class ConversationMemory:
    """Manages multi-turn conversation history with token budgeting."""

    def __init__(self, model: str = "gpt-4o", max_tokens: int = 120_000):
        self.model = model
        self.max_tokens = max_tokens
        self.messages: list[dict] = []
        self._encoder = tiktoken.encoding_for_model(model)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.messages.append({"role": role, "content": content})
        self._trim_if_needed()

    def get_messages(self, system_prompt: str) -> list[dict]:
        """Return full message list including system prompt."""
        return [{"role": "system", "content": system_prompt}] + self.messages

    def count_tokens(self, text: str) -> int:
        """Count tokens in a string."""
        return len(self._encoder.encode(text))

    def total_tokens(self) -> int:
        """Count total tokens across all messages."""
        total = 0
        for m in self.messages:
            content = m.get("content") or ""
            total += self.count_tokens(content)
            # Count tokens in tool call arguments too
            if "tool_calls" in m:
                for tc in m["tool_calls"]:
                    args = tc.get("function", {}).get("arguments", "")
                    total += self.count_tokens(args)
        return total

    def _trim_if_needed(self) -> None:
        """Remove oldest messages (keeping first user message) if over token limit."""
        while self.total_tokens() > self.max_tokens and len(self.messages) > 2:
            # Keep the first message for context, remove the second oldest
            self.messages.pop(1)

    def clear(self) -> None:
        """Clear all conversation history."""
        self.messages = []

    def get_turn_count(self) -> int:
        """Return the number of user messages (turns) in the conversation."""
        return sum(1 for m in self.messages if m["role"] == "user")

    def get_summary(self) -> str:
        """Return a brief summary of the conversation state."""
        return (
            f"Turns: {self.get_turn_count()} | "
            f"Messages: {len(self.messages)} | "
            f"Tokens: {self.total_tokens():,}"
        )
