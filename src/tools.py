"""
Tool Definitions & Execution Engine

Defines the tools CodeBuddy can use via OpenAI's function calling API,
and handles their execution safely.

Tools:
  - run_python: Execute Python code in a sandboxed subprocess
  - analyze_error: Parse a Python traceback and return structured analysis
"""

import subprocess
import sys
import json
import ast
import tempfile
import os
from typing import Any


# Tool Schemas (OpenAI function calling format)

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": (
                "Execute Python code and return the output. Use this when the user "
                "asks you to run, test, or verify code. The code runs in an isolated "
                "subprocess with a 10-second timeout. If the code uses input(), "
                "provide the expected user inputs as a list of strings in the 'user_inputs' parameter."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute",
                    },
                    "user_inputs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "List of inputs to feed to the program if it uses input(). "
                            "Each item corresponds to one input() call in order. "
                            "Example: ['Alice', '25'] for a program that asks for name then age."
                        ),
                    },
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_error",
            "description": (
                "Analyze a Python error traceback and return a structured breakdown "
                "of what went wrong, why, and how to fix it. Use this when the user "
                "shares an error message or traceback."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "error_text": {
                        "type": "string",
                        "description": "The full error message or traceback to analyze",
                    },
                    "code_context": {
                        "type": "string",
                        "description": "The code that produced the error (if available)",
                    },
                },
                "required": ["error_text"],
            },
        },
    },
]


# Tool Implementations

def _auto_print_last_expression(code):
    """
    If the last statement in the code is a bare expression (like a variable,
    dict, list, or function call that returns a value), wrap it in print()
    so the output is captured. Works like a Python REPL.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    if not tree.body:
        return code

    last_node = tree.body[-1]

    if isinstance(last_node, ast.Expr):
        # Skip if it's already a print() call
        if (
            isinstance(last_node.value, ast.Call)
            and isinstance(last_node.value.func, ast.Name)
            and last_node.value.func.id == "print"
        ):
            return code

        # Skip if it's a function call (likely has side effects like printing)
        # Only auto-print variables, literals, and attribute accesses
        if isinstance(last_node.value, ast.Call):
            return code

        lines = code.split("\n")
        last_line_start = last_node.lineno - 1
        last_line_end = last_node.end_lineno

        expr_lines = lines[last_line_start:last_line_end]
        expr_text = "\n".join(expr_lines).strip()

        before = "\n".join(lines[:last_line_start])
        after = "\n".join(lines[last_line_end:])

        wrapped = "print(repr(" + expr_text + "))"
        parts = [p for p in [before, wrapped, after] if p.strip()]
        return "\n".join(parts)

    return code


def run_python(code, user_inputs=None):
    """
    Execute Python code in an isolated subprocess.

    Features:
    - Auto-prints the last expression if it has no print() (like a REPL)
    - Supports user_inputs for code that uses input()
    - Overrides input() to suppress prompt text from polluting stdout
    - 10-second timeout to prevent infinite loops
    - Captures both stdout and stderr
    """
    tmp_path = None
    try:
        processed_code = _auto_print_last_expression(code)

        if user_inputs:
            input_override = (
                "import builtins as _b\n"
                "_original_input = _b.input\n"
                "def _clean_input(prompt=''):\n"
                "    return _original_input()\n"
                "_b.input = _clean_input\n"
            )
            processed_code = input_override + processed_code

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp:
            tmp.write(processed_code)
            tmp_path = tmp.name

        stdin_data = None
        if user_inputs:
            stdin_data = "\n".join(user_inputs) + "\n"

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
            input=stdin_data,
            cwd=tempfile.gettempdir(),
        )

        os.unlink(tmp_path)
        tmp_path = None

        output = result.stdout.strip()
        error = result.stderr.strip()

        response = {}

        if user_inputs:
            response["inputs_provided"] = user_inputs

        if result.returncode == 0:
            response.update({
                "status": "success",
                "output": output if output else "(code executed successfully, no output)",
                "error": None,
            })
        else:
            response.update({
                "status": "error",
                "output": output if output else None,
                "error": error,
            })

        return response

    except subprocess.TimeoutExpired:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return {
            "status": "timeout",
            "output": None,
            "error": "Code execution timed out after 10 seconds. Possible infinite loop.",
        }
    except Exception as e:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return {
            "status": "error",
            "output": None,
            "error": "Execution failed: " + str(e),
        }


def analyze_error(error_text, code_context=""):
    """
    Parse a Python traceback into structured components.
    Returns the error type, message, and line info for the LLM to explain.
    """
    lines = error_text.strip().split("\n")

    error_type = ""
    error_message = ""
    file_info = ""
    line_number = None

    if lines:
        last_line = lines[-1]
        if ":" in last_line:
            parts = last_line.split(":", 1)
            error_type = parts[0].strip()
            error_message = parts[1].strip()
        else:
            error_message = last_line

    for line in lines:
        if 'File "' in line:
            file_info = line.strip()
            if "line " in line:
                try:
                    line_number = int(line.split("line ")[1].split(",")[0])
                except (ValueError, IndexError):
                    pass

    return {
        "error_type": error_type,
        "error_message": error_message,
        "line_number": line_number,
        "file_info": file_info,
        "full_traceback": error_text,
        "code_context": code_context,
    }


# Tool Dispatcher

TOOL_FUNCTIONS = {
    "run_python": run_python,
    "analyze_error": analyze_error,
}


def execute_tool(tool_name, arguments):
    """
    Execute a tool by name with the given arguments.
    Returns a JSON string of the result.
    """
    if tool_name not in TOOL_FUNCTIONS:
        return json.dumps({"error": "Unknown tool: " + tool_name})

    func = TOOL_FUNCTIONS[tool_name]
    result = func(**arguments)
    return json.dumps(result)
