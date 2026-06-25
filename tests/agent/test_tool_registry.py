from pathlib import Path

import logging
import pytest

from biz.agent.tool import Tool, ToolResult
from biz.agent.tool_registry import ToolRegistry
from biz.agent.tools import register_default_tools


class _A(Tool):
    name = "a"
    description = "tool a"
    parameters = {"type": "object", "properties": {}}
    def execute(self, **kwargs):
        return ToolResult(success=True, output="A")


class _B(Tool):
    name = "b"
    description = "tool b"
    parameters = {"type": "object", "properties": {}}
    def execute(self, **kwargs):
        return ToolResult(success=True, output="B")


class TestRegistry:
    def test_register_and_get(self):
        r = ToolRegistry()
        a = _A()
        r.register(a)
        assert r.get("a") is a

    def test_register_duplicate_raises(self):
        r = ToolRegistry()
        r.register(_A())
        with pytest.raises(ValueError):
            r.register(_A())

    def test_get_unknown_returns_none(self):
        r = ToolRegistry()
        assert r.get("nope") is None

    def test_list_schemas(self):
        r = ToolRegistry()
        r.register(_A())
        r.register(_B())
        schemas = r.list_schemas()
        names = {s["function"]["name"] for s in schemas}
        assert names == {"a", "b"}
        for s in schemas:
            assert s["type"] == "function"

    def test_dispatch_returns_tool_result(self):
        r = ToolRegistry()
        r.register(_A())
        from biz.agent.llm_adapter import ToolCall
        call = ToolCall(id="1", name="a", arguments={})
        result = r.dispatch(call)
        assert result.success is True
        assert result.output == "A"

    def test_dispatch_unknown_tool_returns_error_result(self):
        r = ToolRegistry()
        from biz.agent.llm_adapter import ToolCall
        call = ToolCall(id="1", name="ghost", arguments={})
        result = r.dispatch(call)
        assert result.success is False
        assert "unknown tool" in (result.error or "").lower()

    def test_dispatch_isolates_tool_exceptions(self):
        class _Boom(Tool):
            name = "boom"
            description = ""
            parameters = {"type": "object", "properties": {}}
            def execute(self, **kwargs):
                raise RuntimeError("kaboom")
        r = ToolRegistry()
        r.register(_Boom())
        from biz.agent.llm_adapter import ToolCall
        call = ToolCall(id="1", name="boom", arguments={})
        result = r.dispatch(call)
        assert result.success is False
        assert "kaboom" in (result.error or "")

    def test_dispatch_logs_details_at_debug(self, caplog):
        """At DEBUG level, dispatch should log the tool name, args, and result
        length so the full agent trace is greppable from log files."""
        r = ToolRegistry()
        r.register(_A())
        from biz.agent.llm_adapter import ToolCall
        call = ToolCall(id="1", name="a", arguments={"k": "v"})
        with caplog.at_level(logging.DEBUG):
            result = r.dispatch(call)
        assert result.success is True
        debug_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.DEBUG]
        joined = "\n".join(debug_msgs)
        assert "a" in joined  # tool name appears
        assert "v" in joined  # arg value appears
        assert "dispatch" in joined.lower()

    def test_dispatch_does_not_log_details_at_info(self, caplog):
        """At INFO level, dispatch details must stay silent (no per-call noise)."""
        r = ToolRegistry()
        r.register(_A())
        from biz.agent.llm_adapter import ToolCall
        call = ToolCall(id="1", name="a", arguments={})
        with caplog.at_level(logging.INFO):
            result = r.dispatch(call)
        assert result.success is True
        debug_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.DEBUG]
        assert not any("dispatch" in m.lower() for m in debug_msgs)


class TestDefaultToolSet:
    def test_default_registry_excludes_ast_query(self, tmp_path):
        """ast_query was a Python-only tool; for language-agnostic reviews
        the agent uses read_file + run_command(rg/ls/...) instead. This test
        guards against accidental re-registration of the Python-only tool.
        """
        r = ToolRegistry()
        register_default_tools(r, tmp_path)
        assert r.get("ast_query") is None
        # The two language-agnostic tools must still be present.
        assert r.get("read_file") is not None
        assert r.get("run_command") is not None