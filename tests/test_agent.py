"""Tests for ConversationMemory (no API key needed)."""

import pytest
from src.memory import ConversationMemory


class TestConversationMemory:
    def setup_method(self):
        self.memory = ConversationMemory(model="gpt-4o", max_tokens=1000)

    def test_add_message(self):
        self.memory.add_message("user", "Hello")
        assert len(self.memory.messages) == 1
        assert self.memory.messages[0]["role"] == "user"

    def test_get_messages_includes_system(self):
        self.memory.add_message("user", "Hi")
        messages = self.memory.get_messages("You are a bot.")
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_turn_count(self):
        self.memory.add_message("user", "Q1")
        self.memory.add_message("assistant", "A1")
        self.memory.add_message("user", "Q2")
        assert self.memory.get_turn_count() == 2

    def test_clear(self):
        self.memory.add_message("user", "Hello")
        self.memory.clear()
        assert len(self.memory.messages) == 0

    def test_token_counting(self):
        tokens = self.memory.count_tokens("Hello world")
        assert tokens > 0

    def test_trim_on_overflow(self):
        # Use a very small token limit to trigger trimming
        mem = ConversationMemory(model="gpt-4o", max_tokens=50)
        for i in range(20):
            mem.add_message("user", f"Message number {i} with some extra text to use tokens")
        # Should have trimmed down
        assert mem.total_tokens() <= 50 or len(mem.messages) <= 2
