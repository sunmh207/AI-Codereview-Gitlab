"""Agent tool implementations."""
from biz.agent.tool_registry import ToolRegistry
from biz.agent.tools.ast_query import ASTQueryTool
from biz.agent.tools.read_file import ReadFileTool
from biz.agent.tools.run_command import RunCommandTool


def register_default_tools(registry: ToolRegistry, repo_root) -> None:
    """Register the default tool set bound to `repo_root`.

    `repo_root` may be a Path or str. Returns nothing; mutates `registry` in place.
    """
    registry.register(ReadFileTool(repo_root))
    registry.register(ASTQueryTool(repo_root))
    registry.register(RunCommandTool(repo_root))


__all__ = [
    "ReadFileTool",
    "ASTQueryTool",
    "RunCommandTool",
    "register_default_tools",
]