import json
from unittest.mock import MagicMock

import pytest

from biz.agent.llm_adapter import LLMAdapter, LLMResponse, ToolCall


class FakeNativeClient:
    """Client that supports native chat_with_tools."""
    def __init__(self, native_response):
        self._resp = native_response
        self.calls = []

    def chat_with_tools(self, messages, tools=None, model=None):
        self.calls.append({"messages": messages, "tools": tools, "model": model})
        return self._resp


class FakeLegacyClient:
    """Client without chat_with_tools (e.g. ZhipuAI / Ollama stub)."""
    def __init__(self, completions_response):
        self._resp = completions_response
        self.calls = []

    def completions(self, messages, model=None):
        self.calls.append({"messages": messages, "model": model})
        return self._resp


class TestNativeMode:
    def test_parses_native_response(self):
        client = FakeNativeClient({
            "content": "hi",
            "tool_calls": [{"id": "1", "name": "foo", "arguments": {"x": 1}}],
            "raw": object(),
        })
        adapter = LLMAdapter(client)
        resp = adapter.completions_with_tools(
            messages=[{"role": "user", "content": "?"}],
            tools=[{"type": "function", "function": {"name": "foo"}}],
        )
        assert resp.content == "hi"
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].id == "1"
        assert resp.tool_calls[0].name == "foo"
        assert resp.tool_calls[0].arguments == {"x": 1}

    def test_no_tool_calls_returns_content_only(self):
        client = FakeNativeClient({
            "content": "done",
            "tool_calls": [],
            "raw": object(),
        })
        adapter = LLMAdapter(client)
        resp = adapter.completions_with_tools(messages=[{"role": "user", "content": "?"}], tools=[])
        assert resp.content == "done"
        assert resp.tool_calls == []


class TestJsonFallback:
    def test_parses_json_block_in_content(self):
        # Model that doesn't support tool-use emits a JSON block in its content.
        block = json.dumps({"tool": "read_file", "args": {"path": "main.py"}, "id": "abc"})
        content = f"thinking...\n{block}\ndone thinking"
        client = FakeLegacyClient(content)
        adapter = LLMAdapter(client, use_native=False)  # force fallback
        resp = adapter.completions_with_tools(messages=[{"role": "user", "content": "?"}], tools=[])
        assert resp.content is not None
        assert "thinking..." in resp.content
        # Tool call parsed out.
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "read_file"
        assert resp.tool_calls[0].arguments == {"path": "main.py"}
        assert resp.tool_calls[0].id == "abc"

    def test_no_json_block_returns_content(self):
        client = FakeLegacyClient("just plain text, no tools needed")
        adapter = LLMAdapter(client, use_native=False)
        resp = adapter.completions_with_tools(messages=[{"role": "user", "content": "?"}], tools=[])
        assert resp.content == "just plain text, no tools needed"
        assert resp.tool_calls == []

    def test_legacy_client_without_chat_with_tools_falls_back(self):
        # Client that has no chat_with_tools at all.
        client = FakeLegacyClient("ok")
        adapter = LLMAdapter(client)
        # Should not raise; should use completions() and parse JSON-protocol.
        resp = adapter.completions_with_tools(messages=[{"role": "user", "content": "?"}], tools=[])
        assert resp.tool_calls == []


class TestBuildMessages:
    def test_build_assistant_message_with_tool_calls(self):
        adapter = LLMAdapter(FakeNativeClient({"content": "x", "tool_calls": [], "raw": None}))
        resp = LLMResponse(content="x", tool_calls=[ToolCall("1", "foo", {})])
        msg = adapter.build_assistant_message(resp)
        assert msg["role"] == "assistant"
        # Either includes tool_calls (native) or strips JSON block (fallback).
        assert msg.get("content") is not None

    def test_build_tool_message_includes_call_id(self):
        adapter = LLMAdapter(FakeNativeClient({"content": "x", "tool_calls": [], "raw": None}))
        from biz.agent.tool import ToolResult
        msg = adapter.build_tool_message(ToolCall("42", "foo", {}), ToolResult(True, "out"))
        assert msg["role"] == "tool"
        assert msg["tool_call_id"] == "42"
        assert msg["content"] == "out"
