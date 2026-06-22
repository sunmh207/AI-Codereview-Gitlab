import pytest

from biz.agent.tool import Tool, ToolResult


class _EchoTool(Tool):
    name = "echo"
    description = "Echoes back its input."
    parameters = {
        "type": "object",
        "properties": {"msg": {"type": "string"}},
        "required": ["msg"],
    }

    def execute(self, **kwargs):
        return ToolResult(success=True, output=kwargs["msg"])


class TestTool:
    def test_subclass_must_implement_execute(self):
        class _Bad(Tool):
            name = "bad"
            description = ""
            parameters = {}
        with pytest.raises(TypeError):
            _Bad()  # type: ignore[abstract]

    def test_concrete_tool_runs(self):
        t = _EchoTool()
        r = t.execute(msg="hi")
        assert r.success is True
        assert r.output == "hi"

    def test_to_schema(self):
        t = _EchoTool()
        schema = t.to_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "echo"
        assert schema["function"]["description"] == "Echoes back its input."
        assert "msg" in schema["function"]["parameters"]["properties"]
