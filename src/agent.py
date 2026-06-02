"""
Multi-Turn Conversational Agent

Core agent class that handles conversation flow with OpenAI's GPT-4o,
maintains context across turns, streams responses, and executes tools
via function calling.
"""

import json
from openai import OpenAI
from typing import Generator

from src.config import OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS
from src.memory import ConversationMemory
from src.prompts import SYSTEM_PROMPT
from src.tools import TOOL_SCHEMAS, execute_tool


class CodingAgent:
    """A multi-turn coding assistant powered by GPT-4o with tool use."""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.memory = ConversationMemory(model=self.model)
        self.last_tool_calls = []  # Track tool calls for UI display

    def chat(self, user_message: str) -> str:
        """Send a message and get a complete response (with tool use)."""
        self.memory.add_message("user", user_message)
        self.last_tool_calls = []

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.memory.get_messages(SYSTEM_PROMPT),
            max_tokens=MAX_TOKENS,
            temperature=0.7,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        # Handle the tool calling loop
        message = response.choices[0].message

        while message.tool_calls:
            # Add assistant's tool call message to memory
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

            # Execute each tool call
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

                # Execute and get result
                result = execute_tool(func_name, func_args)

                # Track for UI
                self.last_tool_calls.append({
                    "name": func_name,
                    "arguments": func_args,
                    "result": json.loads(result),
                })

                # Add tool result to memory
                self.memory.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            # Call the model again with tool results
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.memory.get_messages(SYSTEM_PROMPT),
                max_tokens=MAX_TOKENS,
                temperature=0.7,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            message = response.choices[0].message

        # Final text response
        assistant_message = message.content or ""
        self.memory.add_message("assistant", assistant_message)

        return assistant_message

    def chat_stream(self, user_message: str) -> Generator[str, None, None]:
        """
        Send a message with tool use support + streaming for the final response.

        Flow:
        1. Call OpenAI (non-streamed) to check if tools are needed
        2. If tools → execute them, loop back
        3. Once no more tools → stream the final response
        """
        self.memory.add_message("user", user_message)
        self.last_tool_calls = []

        # Step 1: Non-streamed call to check for tool use
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.memory.get_messages(SYSTEM_PROMPT),
            max_tokens=MAX_TOKENS,
            temperature=0.7,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        message = response.choices[0].message

        # Step 2: Tool execution loop (non-streamed)
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
                messages=self.memory.get_messages(SYSTEM_PROMPT),
                max_tokens=MAX_TOKENS,
                temperature=0.7,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            message = response.choices[0].message

        # Step 3: Stream the final text response
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

    def get_last_tool_calls(self) -> list[dict]:
        """Return tool calls from the last interaction (for UI display)."""
        return self.last_tool_calls

    def reset(self) -> None:
        """Reset the conversation history."""
        self.memory.clear()
        self.last_tool_calls = []

    def get_stats(self) -> str:
        """Return conversation statistics."""
        return self.memory.get_summary()
