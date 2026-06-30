"""Agentic reverse-engineering assistant.

Talks to an OpenAI-compatible LLM and lets it drive a headless Ghidra REST
service through function calls. Settings (LLM endpoint, model, Ghidra URL) are
read fresh on every request, so changes made in the UI take effect immediately
without a restart.
"""
import json
import os
from typing import Any, Dict, Generator

import requests
from openai import OpenAI

from .config import load_settings
from .paths import user_data_dir

SYSTEM_PROMPT = (
    "You are a helpful reverse engineering assistant. You have access to a set of "
    "tools to analyze a binary identified by a job_id. When the user asks a "
    "question, use the available tools to find the answer. If something is not "
    "clear, ask for clarification before answering. Format your final response in "
    "Markdown. You can generate Call Graphs or Flowcharts using Mermaid.js syntax "
    "(wrap in ```mermaid code block) to visualize function relationships or logic "
    "flow."
)

TOOLS = [
    {"type": "function", "function": {"name": "analyze", "description": "Upload a base64-encoded binary and start headless Ghidra analysis. Returns job_id.", "parameters": {"type": "object", "properties": {"file_b64": {"type": "string"}, "filename": {"type": "string"}}, "required": ["file_b64", "filename"]}}},
    {"type": "function", "function": {"name": "status", "description": "Get status for an existing analysis job.", "parameters": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}}},
    {"type": "function", "function": {"name": "list_functions", "description": "Retrieve a paginated list of discovered functions for a job. Use offset/limit to page through results.", "parameters": {"type": "object", "properties": {"job_id": {"type": "string"}, "offset": {"type": "integer"}, "limit": {"type": "integer"}}, "required": ["job_id"]}}},
    {"type": "function", "function": {"name": "decompile_function", "description": "Get decompiled pseudocode for a function at a given address.", "parameters": {"type": "object", "properties": {"job_id": {"type": "string"}, "addr": {"type": "string"}}, "required": ["job_id", "addr"]}}},
    {"type": "function", "function": {"name": "get_xrefs", "description": "Get callers and callees for a function (cross-references).", "parameters": {"type": "object", "properties": {"job_id": {"type": "string"}, "addr": {"type": "string"}}, "required": ["job_id", "addr"]}}},
    {"type": "function", "function": {"name": "list_imports", "description": "List imported libraries and symbols for the binary.", "parameters": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}}},
    {"type": "function", "function": {"name": "list_strings", "description": "Return printable strings extracted from the binary.", "parameters": {"type": "object", "properties": {"job_id": {"type": "string"}, "min_length": {"type": "integer"}}, "required": ["job_id"]}}},
    {"type": "function", "function": {"name": "query_artifacts", "description": "Search artifacts (functions, strings) for a pattern. Supports regex.", "parameters": {"type": "object", "properties": {"job_id": {"type": "string"}, "query": {"type": "string"}, "regex": {"type": "boolean"}}, "required": ["job_id", "query"]}}},
]

# Functions the agent is allowed to actually invoke (analyze is handled by /upload).
TOOL_NAMES = [
    "status", "list_functions", "decompile_function", "get_xrefs",
    "list_imports", "list_strings", "query_artifacts",
]

TOOL_INTENT_DESCRIPTIONS = {
    "list_functions": "Получаю список функций бинарника.",
    "decompile_function": "Декомпилирую функцию, чтобы прочитать код.",
    "get_xrefs": "Смотрю перекрёстные ссылки (кто вызывает функцию).",
    "list_imports": "Перечисляю импортируемые библиотеки и функции.",
    "list_strings": "Ищу интересные строки в бинарнике.",
    "query_artifacts": "Выполняю поиск по артефактам.",
    "status": "Проверяю статус анализа.",
}


def call_ghidra_tool(base_url: str, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        response = requests.post(f"{base_url}/tools/{endpoint}", json=payload, timeout=120)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"result": response.text}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


class GhidraAssistant:
    def __init__(self):
        self.chats_dir = os.path.join(user_data_dir(), "chats")
        os.makedirs(self.chats_dir, exist_ok=True)

    # ----- history persistence -------------------------------------------------
    def _get_chat_file(self, job_id: str) -> str:
        return os.path.join(self.chats_dir, f"{job_id}.json")

    def load_history(self, job_id: str) -> list:
        chat_file = self._get_chat_file(job_id)
        if os.path.exists(chat_file):
            try:
                with open(chat_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_history(self, job_id: str, messages: list):
        with open(self._get_chat_file(job_id), "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)

    # ----- chat ----------------------------------------------------------------
    def chat_completion_stream(self, user_message: str, job_id: str) -> Generator[str, None, None]:
        settings = load_settings()
        client = OpenAI(
            base_url=settings["llm_base_url"],
            api_key=settings.get("llm_api_key") or "not-used",
        )
        model = settings["llm_model"]
        ghidra_base = settings["ghidra_base_url"]
        max_turns = settings["max_agent_turns"]
        available_tools = {
            name: (lambda n: lambda **kw: call_ghidra_tool(ghidra_base, n, kw))(name)
            for name in TOOL_NAMES
        }

        history = self.load_history(job_id)
        if not history:
            history.append({"role": "system", "content": SYSTEM_PROMPT})
        if history[0]["role"] != "system":
            history.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

        history.append({"role": "user", "content": f"[Job ID: {job_id}] {user_message}"})
        messages = history

        for _ in range(max_turns):
            try:
                response = client.chat.completions.create(
                    model=model, messages=messages, tools=TOOLS, tool_choice="auto"
                )
            except Exception as e:
                yield json.dumps({"type": "error", "content": f"LLM Error: {str(e)}"})
                return

            message = response.choices[0].message
            messages.append(message)

            if not message.tool_calls:
                if message.content:
                    yield json.dumps({"type": "token", "content": message.content})
                break

            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                if function_name not in available_tools:
                    continue
                intent = TOOL_INTENT_DESCRIPTIONS.get(
                    function_name, f"Выполняю инструмент: {function_name}…"
                )
                yield json.dumps({"type": "tool_call", "description": intent})

                try:
                    args = json.loads(tool_call.function.arguments)
                except Exception:
                    args = {}
                args["job_id"] = job_id

                result = available_tools[function_name](**args)
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(result),
                })

        # Final streamed answer.
        complete_response = ""
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    complete_response += content
                    yield json.dumps({"type": "token", "content": content})
        except Exception as e:
            yield json.dumps({"type": "error", "content": f"LLM Error: {str(e)}"})
            return

        messages.append({"role": "assistant", "content": complete_response})
        self.save_history(job_id, _serialize(messages))


def _serialize(messages: list) -> list:
    """Turn a mix of dicts and OpenAI SDK message objects into plain JSON."""
    out = []
    for m in messages:
        if isinstance(m, dict):
            out.append(m)
            continue
        d = {"role": m.role, "content": m.content}
        if getattr(m, "tool_calls", None):
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in m.tool_calls
            ]
        out.append(d)
    return out
