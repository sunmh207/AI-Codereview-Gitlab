from unittest.mock import MagicMock

import logging
import pytest

from biz.agent.llm_adapter import LLMAdapter, LLMResponse, ToolCall
from biz.agent.runner import AgentRunner
from biz.agent.tool import Tool, ToolResult
from biz.agent.tool_registry import ToolRegistry


class _CounterTool(Tool):
    """A tool that returns its 'n' argument as output."""
    name = "counter"
    description = "returns n"
    parameters = {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]}

    def execute(self, **kwargs):
        return ToolResult(True, str(kwargs["n"]))


def _adapter_returning(responses):
    """Build a mock client that returns the next response each call."""
    client = MagicMock()
    client.chat_with_tools.side_effect = responses
    return client


class TestAgentRunner:
    def test_single_round_terminates_with_content(self):
        client = _adapter_returning([
            {"content": "done", "tool_calls": [], "raw": None},
        ])
        adapter = LLMAdapter(client, use_native=True)
        runner = AgentRunner(adapter=adapter, registry=ToolRegistry(), max_iterations=5)
        result = runner.run([{"role": "user", "content": "hi"}])
        assert result == "done"
        assert client.chat_with_tools.call_count == 1

    def test_multi_round_with_tools(self):
        responses = [
            {"content": "calling counter", "tool_calls": [
                {"id": "1", "name": "counter", "arguments": {"n": 42}},
            ], "raw": None},
            {"content": "the answer is 42", "tool_calls": [], "raw": None},
        ]
        client = _adapter_returning(responses)
        adapter = LLMAdapter(client, use_native=True)
        reg = ToolRegistry()
        reg.register(_CounterTool())
        runner = AgentRunner(adapter=adapter, registry=reg, max_iterations=5)
        result = runner.run([{"role": "user", "content": "?"}])
        assert "42" in result
        assert client.chat_with_tools.call_count == 2

    def test_max_iterations_returns_last_assistant_content(self):
        # Always returns a tool call.
        responses = [
            {"content": None, "tool_calls": [
                {"id": str(i), "name": "counter", "arguments": {"n": i}},
            ], "raw": None}
            for i in range(3)
        ]
        client = _adapter_returning(responses)
        adapter = LLMAdapter(client, use_native=True)
        reg = ToolRegistry()
        reg.register(_CounterTool())
        runner = AgentRunner(adapter=adapter, registry=reg, max_iterations=3)
        result = runner.run([{"role": "user", "content": "?"}])
        # 3 rounds hit, last assistant content was None; loop terminated.
        assert "max iterations" in result.lower()
        assert client.chat_with_tools.call_count == 3

    def test_tool_exception_isolated(self):
        class _Boom(Tool):
            name = "boom"
            description = ""
            parameters = {"type": "object", "properties": {}}
            def execute(self, **kwargs):
                raise RuntimeError("explode")
        responses = [
            {"content": "trying", "tool_calls": [
                {"id": "1", "name": "boom", "arguments": {}},
            ], "raw": None},
            {"content": "done", "tool_calls": [], "raw": None},
        ]
        client = _adapter_returning(responses)
        adapter = LLMAdapter(client, use_native=True)
        reg = ToolRegistry()
        reg.register(_Boom())
        runner = AgentRunner(adapter=adapter, registry=reg, max_iterations=5)
        # Should not raise.
        result = runner.run([{"role": "user", "content": "?"}])
        assert result == "done"

    def test_token_cap_triggers_degradation(self):
        # Force a very low cap so the first tool result already blows it.
        from biz.agent.runner import AgentRunner as AR
        responses = [
            {"content": "calling", "tool_calls": [
                {"id": "1", "name": "counter", "arguments": {"n": 1}},
            ], "raw": None},
            {"content": "done", "tool_calls": [], "raw": None},
        ]
        client = _adapter_returning(responses)
        adapter = LLMAdapter(client, use_native=True)
        reg = ToolRegistry()
        reg.register(_CounterTool())
        runner = AR(adapter=adapter, registry=reg, max_iterations=5, total_token_cap=1)
        with pytest.raises(TokenBudgetExceeded):
            runner.run([{"role": "user", "content": "?"}])

    def test_three_empty_rounds_raises_streak(self):
        # Three rounds with neither content nor tool_calls.
        from biz.agent.runner import InvalidToolCallStreak
        responses = [
            {"content": None, "tool_calls": [], "raw": None},
            {"content": "", "tool_calls": [], "raw": None},
            {"content": "", "tool_calls": [], "raw": None},
        ]
        client = _adapter_returning(responses)
        adapter = LLMAdapter(client, use_native=True)
        runner = AgentRunner(adapter=adapter, registry=ToolRegistry(), max_iterations=10)
        with pytest.raises(InvalidToolCallStreak):
            runner.run([{"role": "user", "content": "?"}])

    def test_runner_logs_round_details_at_debug(self, caplog):
        """At DEBUG level the runner should emit per-round detail (assistant
        content + tool name/args) so operators can grep the full agent trace
        when an agentic review misbehaves. INFO must stay quiet for these.
        """
        responses = [
            {"content": "calling counter", "tool_calls": [
                {"id": "1", "name": "counter", "arguments": {"n": 7}},
            ], "raw": None},
            {"content": "the answer is 7", "tool_calls": [], "raw": None},
        ]
        client = _adapter_returning(responses)
        adapter = LLMAdapter(client, use_native=True)
        reg = ToolRegistry()
        reg.register(_CounterTool())
        runner = AgentRunner(adapter=adapter, registry=reg, max_iterations=5)

        with caplog.at_level(logging.DEBUG):
            runner.run([{"role": "user", "content": "?"}])

        debug_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.DEBUG]
        # Per-round detail must include the tool name and the assistant content.
        joined = "\n".join(debug_msgs)
        assert "counter" in joined
        assert "the answer is 7" in joined

    def test_runner_does_not_log_round_details_at_info(self, caplog):
        """At INFO level the per-round detail line must NOT fire — only the
        existing one-line summary belongs to INFO. (Caplog level is INFO.)"""
        responses = [
            {"content": "calling counter", "tool_calls": [
                {"id": "1", "name": "counter", "arguments": {"n": 7}},
            ], "raw": None},
            {"content": "the answer is 7", "tool_calls": [], "raw": None},
        ]
        client = _adapter_returning(responses)
        adapter = LLMAdapter(client, use_native=True)
        reg = ToolRegistry()
        reg.register(_CounterTool())
        runner = AgentRunner(adapter=adapter, registry=reg, max_iterations=5)

        with caplog.at_level(logging.INFO):
            runner.run([{"role": "user", "content": "?"}])

        info_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
        assert any("agent round" in m for m in info_msgs), "expected existing INFO summary"
        debug_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.DEBUG]
        assert not debug_msgs, f"DEBUG messages leaked at INFO level: {debug_msgs}"

    def test_tool_output_truncated_to_max_tokens(self):
        # Big payload via a tool that returns a large string; runner should truncate.
        class _BigTool(Tool):
            name = "big"
            description = ""
            parameters = {"type": "object", "properties": {}}
            def execute(self, **kwargs):
                return ToolResult(True, "x" * 200_000)

        responses = [
            {"content": "calling", "tool_calls": [
                {"id": "1", "name": "big", "arguments": {}},
            ], "raw": None},
            {"content": "done", "tool_calls": [], "raw": None},
        ]
        client = _adapter_returning(responses)
        adapter = LLMAdapter(client, use_native=True)
        reg = ToolRegistry()
        reg.register(_BigTool())
        runner = AgentRunner(
            adapter=adapter, registry=reg, max_iterations=5,
            tool_output_max_tokens=50,
        )
        result = runner.run([{"role": "user", "content": "?"}])
        assert result == "done"
        # Find the tool message in the call args and assert truncation marker.
        second_call = client.chat_with_tools.call_args_list[1]
        sent_messages = second_call.kwargs["messages"]
        tool_msg = next(m for m in sent_messages if m.get("role") == "tool")
        assert "[output truncated]" in tool_msg["content"]
        assert len(tool_msg["content"]) < 1000


# Imported here so pytest can collect the symbol from the module.
from biz.agent.runner import TokenBudgetExceeded, InvalidToolCallStreak  # noqa: E402,F401