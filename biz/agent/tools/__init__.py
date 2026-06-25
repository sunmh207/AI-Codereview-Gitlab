"""Agent tool implementations."""
from biz.agent.tool_registry import ToolRegistry
from biz.agent.tools.read_file import ReadFileTool
from biz.agent.tools.run_command import RunCommandTool


def register_default_tools(
    registry: ToolRegistry,
    repo_root,
    *,
    allowlist: list[str] | None = None,
    blocklist: list[str] | None = None,
) -> None:
    """Register the default tool set bound to `repo_root`.

    `repo_root` may be a Path or str. `allowlist`/`blocklist` (if provided)
    override the RunCommandTool defaults. Returns nothing; mutates `registry`
    in place.
    """
    registry.register(ReadFileTool(repo_root))
    registry.register(RunCommandTool(repo_root, allowlist=allowlist, blocklist=blocklist))


__all__ = [
    "ReadFileTool",
    "RunCommandTool",
    "register_default_tools",
]