"""Registry mapping tool names to Tool instances."""
from __future__ import annotations

from typing import Any

from biz.agent.tool import Tool, ToolResult
from biz.utils.log import logger


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool {tool.name!r} already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_schemas(self) -> list[dict]:
        return [t.to_schema() for t in self._tools.values()]

    def dispatch(self, call: Any) -> ToolResult:
        """Execute the named tool. Exceptions in tools are caught and returned as
        ToolResult(success=False, error=...).
        """
        tool = self._tools.get(call.name)
        if tool is None:
            logger.debug("tool dispatch: name=%s args=%s -> unknown tool",
                         call.name, call.arguments)
            return ToolResult(success=False, output="", error=f"unknown tool: {call.name}")
        try:
            result = tool.execute(**call.arguments)
            if not isinstance(result, ToolResult):
                # Defensive: tools should return ToolResult.
                result = ToolResult(success=True, output=str(result))
        except Exception as e:
            logger.exception("tool %s raised", call.name)
            result = ToolResult(success=False, output="", error=f"{type(e).__name__}: {e}")
        # DEBUG: per-dispatch trace so the full agent run is greppable.
        # INFO users don't see this; only those who set LOG_LEVEL=DEBUG.
        logger.debug(
            "tool dispatch: name=%s args=%s success=%s result_len=%d error=%s",
            call.name, call.arguments, result.success,
            len(result.output or ""), result.error or "",
        )
        return result