"""
Multi-Turn Conversational Agent

Core agent class that handles conversation flow with OpenAI's GPT-4o,
maintains context across turns, streams responses, executes tools
via function calling, and retrieves relevant context via RAG.
"""

import json
from openai import OpenAI
from typing import Generator

from src.config import OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS
from src.memory import ConversationMemory
from src.prompts import SYSTEM_PROMPT, RAG_CONTEXT_TEMPLATE
from src.tools import TOOL_SCHEMAS, execute_tool
from src.rag import RAGEngine


class CodingAgent:
    """A multi-turn coding assistant powered by GPT-4o with tool use and RAG."""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.memory = ConversationMemory(model=self.model)
        self.rag = RAGEngine()
        self.last_tool_calls = []

    def _build_system_prompt(self, user_message: str) -> str:
        """
        Build the system prompt, injecting RAG context if documents are indexed.
        """
        prompt = SYSTEM_PROMPT

        if self.rag.has_documents():
            # Search for relevant chunks
            results = self.rag.search(user_message)
            if results:
                context = self.rag.format_context(results)
                prompt += RAG_CONTEXT_TEMPLATE.format(context=context)

        return prompt

    def chat(self, user_message: str) -> str:
        """Send a message and get a complete response (with tool use + RAG)."""
        self.memory.add_message("user", user_message)
        self.last_tool_calls = []

        system_prompt = self._build_system_prompt(user_message)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.memory.get_messages(system_prompt),
            max_tokens=MAX_TOKENS,
            temperature=0.7,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        message = response.choices[0].message

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

        assistant_message = message.content or ""
        self.memory.add_message("assistant", assistant_message)

        return assistant_message

    def chat_stream(self, user_message: str) -> Generator[str, None, None]:
        """
        Send a message with tool use + RAG support + streaming for the final response.
        """
        self.memory.add_message("user", user_message)
        self.last_tool_calls = []

        system_prompt = self._build_system_prompt(user_message)

        # Step 1: Non-streamed call to check for tool use
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.memory.get_messages(system_prompt),
            max_tokens=MAX_TOKENS,
            temperature=0.7,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        message = response.choices[0].message

        # Step 2: Tool execution loop
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

        # Step 3: Stream the final text response
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

    def index_file(self, filename: str, content: bytes) -> int:
        """Index a file for RAG. Returns number of chunks created."""
        return self.rag.index_file(filename, content)

    def get_rag_stats(self) -> dict:
        """Return RAG indexing statistics."""
        return self.rag.get_stats()

    def clear_rag(self) -> None:
        """Clear all indexed documents."""
        self.rag.clear()

    def get_last_tool_calls(self) -> list[dict]:
        """Return tool calls from the last interaction."""
        return self.last_tool_calls

    def reset(self) -> None:
        """Reset conversation history and RAG index."""
        self.memory.clear()
        self.rag.clear()
        self.last_tool_calls = []

    def get_stats(self) -> str:
        """Return conversation statistics."""
        return self.memory.get_summary()
