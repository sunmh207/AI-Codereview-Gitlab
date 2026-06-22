import pytest

from biz.agent.tool import Tool, ToolResult
from biz.agent.tool_registry import ToolRegistry


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