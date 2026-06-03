"""
Multi-Turn Conversational Agent

Core agent class that handles conversation flow with OpenAI's GPT-4o,
maintains context across turns, streams responses, executes tools
via function calling, retrieves relevant context via RAG, and
persists conversations to SQLite.
"""

import json
from openai import OpenAI
from typing import Generator

from src.config import OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS
from src.memory import ConversationMemory
from src.prompts import SYSTEM_PROMPT, RAG_CONTEXT_TEMPLATE
from src.tools import TOOL_SCHEMAS, execute_tool
from src.rag import RAGEngine
from src.database import ChatDatabase


class CodingAgent:
    """A multi-turn coding assistant powered by GPT-4o with tool use, RAG, and persistence."""

    def __init__(self, session_id=None):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.memory = ConversationMemory(model=self.model)
        self.rag = RAGEngine()
        self.db = ChatDatabase()
        self.last_tool_calls = []

        if session_id:
            self.session_id = session_id
            self._load_session()
        else:
            self.session_id = self.db.create_session()

    def _load_session(self):
        """Load messages from database into memory."""
        messages = self.db.get_messages(self.session_id)
        for msg in messages:
            if msg["role"] in ("user", "assistant"):
                self.memory.add_message(msg["role"], msg["content"])

    def _persist_message(self, role, content, metadata=None):
        """Save a message to the database."""
        self.db.add_message(self.session_id, role, content, metadata)

    def _build_system_prompt(self, user_message):
        """Build the system prompt, injecting RAG context if documents are indexed."""
        prompt = SYSTEM_PROMPT
        if self.rag.has_documents():
            results = self.rag.search(user_message)
            if results:
                context = self.rag.format_context(results)
                prompt += RAG_CONTEXT_TEMPLATE.format(context=context)
        return prompt

    def _handle_tool_loop(self, message, system_prompt):
        """Handle the tool calling loop. Returns the final message."""
        while message.tool_calls:
            self.memory.messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                result = execute_tool(func_name, func_args)

                self.last_tool_calls.append({
                    "name": func_name,
                    "arguments": func_args,
                    "result": json.loads(result),
                })

                self.memory.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.memory.get_messages(system_prompt),
                max_tokens=MAX_TOKENS,
                temperature=0.7,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            message = response.choices[0].message

        return message

    def chat(self, user_message):
        """Send a message and get a complete response."""
        self.memory.add_message("user", user_message)
        self._persist_message("user", user_message)
        self.last_tool_calls = []

        if self.memory.get_turn_count() == 1:
            self.db.auto_title(self.session_id, user_message)

        system_prompt = self._build_system_prompt(user_message)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.memory.get_messages(system_prompt),
            max_tokens=MAX_TOKENS,
            temperature=0.7,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        message = self._handle_tool_loop(response.choices[0].message, system_prompt)

        assistant_message = message.content or ""
        self.memory.add_message("assistant", assistant_message)
        self._persist_message("assistant", assistant_message)

        return assistant_message

    def chat_stream(self, user_message):
        """Send a message with tool use + RAG + streaming for the final response."""
        self.memory.add_message("user", user_message)
        self._persist_message("user", user_message)
        self.last_tool_calls = []

        if self.memory.get_turn_count() == 1:
            self.db.auto_title(self.session_id, user_message)

        system_prompt = self._build_system_prompt(user_message)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.memory.get_messages(system_prompt),
            max_tokens=MAX_TOKENS,
            temperature=0.7,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        message = self._handle_tool_loop(response.choices[0].message, system_prompt)

        # Stream the final text response
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=self.memory.get_messages(system_prompt),
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
        self._persist_message("assistant", full_response)

    def index_file(self, filename, content):
        """Index a file for RAG. Returns number of chunks created."""
        return self.rag.index_file(filename, content)

    def get_rag_stats(self):
        """Return RAG indexing statistics."""
        return self.rag.get_stats()

    def clear_rag(self):
        """Clear all indexed documents."""
        self.rag.clear()

    def get_last_tool_calls(self):
        """Return tool calls from the last interaction."""
        return self.last_tool_calls

    def reset(self):
        """Reset conversation history and RAG index."""
        self.memory.clear()
        self.rag.clear()
        self.last_tool_calls = []

    def new_session(self):
        """Start a fresh session. Returns the new session ID."""
        self.memory.clear()
        self.last_tool_calls = []
        self.session_id = self.db.create_session()
        return self.session_id

    def switch_session(self, session_id):
        """Switch to an existing session, loading its messages."""
        self.memory.clear()
        self.last_tool_calls = []
        self.session_id = session_id
        self._load_session()

    def list_sessions(self, limit=20):
        """List recent chat sessions."""
        return self.db.list_sessions(limit)

    def delete_session(self, session_id):
        """Delete a session. If current, start a new one."""
        self.db.delete_session(session_id)
        if session_id == self.session_id:
            self.new_session()

    def get_stats(self):
        """Return conversation statistics."""
        return self.memory.get_summary()
