"""LLM output normalization + tool-use protocol across providers.

Wraps an existing ``BaseClient`` (from ``biz.llm.factory``) and:
  - calls ``chat_with_tools()`` if the provider supports it natively
  - otherwise falls back to JSON-protocol: instructs the model to emit
    ``{"tool": "<name>", "args": {...}, "id": "<id>"}`` JSON blocks in its
    content and parses them.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from biz.agent.tool import ToolResult

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall]
    raw: Any = None


# Matches a JSON object with "tool" / "args" / optional "id".
# Allows up to one level of nested braces (for the "args" value).
_JSON_TOOL_BLOCK = re.compile(
    r"\{(?:[^{}]|\{[^{}]*\})*?\"tool\"\s*:\s*\"[^\"]+\"(?:[^{}]|\{[^{}]*\})*?\}",
    re.DOTALL,
)

# Injects JSON-protocol instructions into the system message.
_JSON_PROTOCOL_INSTRUCTION = (
    "\n\nWhen you need to call a tool, emit a single JSON object on its own "
    "line, of the form:\n"
    '{"tool": "<tool_name>", "args": {<json_args>}, "id": "<unique_id>"}\n'
    "Otherwise respond with plain text. Do NOT wrap JSON in markdown fences."
)


class LLMAdapter:
    """Wrap a BaseClient and provide a uniform ``completions_with_tools``."""

    def __init__(self, client, use_native: bool | None = None):
        self.client = client
        # If use_native is None, auto-detect: True if chat_with_tools exists
        # and isn't just the base default.
        if use_native is None:
            use_native = hasattr(client, "chat_with_tools") and callable(
                getattr(client, "chat_with_tools", None)
            )
            # Some clients have chat_with_tools but it's the base NotImpl — detect by checking override.
            if use_native:
                method = getattr(client, "chat_with_tools")
                # Heuristic: if the method is the base class's, fall back.
                # We can detect this by checking if calling it raises NotImplementedError on a stub.
                try:
                    method(messages=[], tools=None)
                except NotImplementedError:
                    use_native = False
                except Exception:
                    pass  # any other error means the method is actually overridden
        self.use_native = use_native

    # ---- public API --------------------------------------------------------

    def completions_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        if self.use_native:
            return self._native(messages, tools)
        return self._json_fallback(messages, tools)

    def build_assistant_message(self, resp: LLMResponse) -> dict:
        if self.use_native:
            return {
                "role": "assistant",
                "content": resp.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for tc in resp.tool_calls
                ],
            }
        # Fallback: strip JSON tool blocks from content; the JSON itself is
        # captured by the next tool_message round-trip.
        content = resp.content or ""
        for tc in resp.tool_calls:
            content = content.replace(tc.raw_block, "") if hasattr(tc, "raw_block") else content
        return {"role": "assistant", "content": content.strip()}

    def build_tool_message(self, call: ToolCall, result: ToolResult) -> dict:
        body = result.output if result.success else f"ERROR: {result.error}"
        return {
            "role": "tool",
            "tool_call_id": call.id,
            "content": body,
        }

    # ---- internals ---------------------------------------------------------

    def _native(self, messages, tools):
        raw = self.client.chat_with_tools(messages=messages, tools=tools)
        return LLMResponse(
            content=raw.get("content"),
            tool_calls=[
                ToolCall(id=tc["id"], name=tc["name"], arguments=tc.get("arguments") or {})
                for tc in raw.get("tool_calls", [])
            ],
            raw=raw.get("raw"),
        )

    def _json_fallback(self, messages, tools):
        # Inject the JSON protocol instruction into the system message (first one).
        if messages and messages[0].get("role") == "system":
            messages = list(messages)
            messages[0] = {**messages[0], "content": messages[0]["content"] + _JSON_PROTOCOL_INSTRUCTION}
        else:
            messages = [{"role": "system", "content": _JSON_PROTOCOL_INSTRUCTION.lstrip()}] + list(messages)
        text = self.client.completions(messages=messages)
        tool_calls: list[ToolCall] = []
        for m in _JSON_TOOL_BLOCK.finditer(text):
            block = m.group(0)
            try:
                obj = json.loads(block)
            except json.JSONDecodeError:
                continue
            name = obj.get("tool")
            args = obj.get("args", {})
            call_id = obj.get("id") or f"call_{len(tool_calls)}"
            if not name or not isinstance(args, dict):
                continue
            tc = ToolCall(id=call_id, name=name, arguments=args)
            tc.raw_block = block  # attached so build_assistant_message can strip
            tool_calls.append(tc)
        # Strip the tool blocks from the content we return (so the next assistant
        # turn in messages has clean prose).
        cleaned = _JSON_TOOL_BLOCK.sub("", text).strip()
        return LLMResponse(content=cleaned, tool_calls=tool_calls, raw=text)
