"""read_file tool: read file contents within the repo."""
from __future__ import annotations

from pathlib import Path

from biz.agent.safety import is_path_safe, is_sensitive_path
from biz.agent.tool import Tool, ToolResult

_BINARY_SAMPLE_BYTES = 8192
_BINARY_NUL_THRESHOLD = 0.10  # >10% NUL bytes => binary


class ReadFileTool(Tool):
    name = "read_file"
    description = (
        "Read a file from the repository. Returns the requested lines "
        "with line numbers. Use offset and limit to page through large files."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path relative to the repository root.",
            },
            "offset": {
                "type": "integer",
                "description": "Zero-based line offset to start reading from.",
                "default": 0,
                "minimum": 0,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to return.",
                "default": 500,
                "minimum": 1,
                "maximum": 5000,
            },
        },
        "required": ["path"],
    }

    def __init__(self, repo_root: Path | str) -> None:
        self.repo_root = Path(repo_root)

    def execute(self, *, path: str, offset: int = 0, limit: int = 500, **_) -> ToolResult:
        # Resolve target inside repo.
        candidate = (self.repo_root / path).resolve(strict=False)
        if not is_path_safe(candidate, self.repo_root):
            return ToolResult(False, "", "path outside repo root")
        if is_sensitive_path(candidate):
            return ToolResult(False, "", "path is sensitive and cannot be read")
        if not candidate.exists() or not candidate.is_file():
            return ToolResult(False, "", f"file not found: {path}")

        # Binary detection on first 8KB.
        try:
            with open(candidate, "rb") as f:
                sample = f.read(_BINARY_SAMPLE_BYTES)
        except OSError as e:
            return ToolResult(False, "", f"read error: {e}")
        if sample:
            nul_ratio = sample.count(b"\x00") / len(sample)
            if nul_ratio > _BINARY_NUL_THRESHOLD:
                return ToolResult(False, "", "binary file, not readable")

        try:
            text = sample.decode("utf-8", errors="replace") if sample else ""
            with open(candidate, "r", encoding="utf-8", errors="replace") as f:
                # Skip the bytes we already read.
                if sample:
                    f.seek(len(sample))
                rest = f.read()
            text = (text + rest) if text or rest else ""
        except OSError as e:
            return ToolResult(False, "", f"read error: {e}")

        lines = text.splitlines()
        start = max(0, int(offset))
        end = min(len(lines), start + int(limit))
        selected = lines[start:end]
        # 1-based line numbers in output.
        first_num = start + 1
        last_num = end
        body = "\n".join(selected)
        return ToolResult(True, f"lines {first_num}-{last_num}:\n{body}")
