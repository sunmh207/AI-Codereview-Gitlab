"""ast_query tool: Python AST-based semantic queries (definitions/references/callees)."""
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

from biz.agent.safety import is_path_safe
from biz.agent.tool import Tool, ToolResult


class ASTQueryTool(Tool):
    name = "ast_query"
    description = (
        "Run a semantic query over Python source code. Supported queries: "
        "'definitions' (list functions/classes), 'references <symbol>' "
        "(find usages), 'callees <func_name>' (list calls inside a function)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Query string, e.g. 'definitions', 'references Foo', 'callees bar'.",
            },
            "path": {
                "type": "string",
                "description": "File or directory (relative to repo root). Default '.'.",
                "default": ".",
            },
            "symbol": {
                "type": "string",
                "description": "Symbol name for 'references' queries. Optional; may be embedded in query.",
                "default": "",
            },
            "func_name": {
                "type": "string",
                "description": "Function name for 'callees' queries. Optional; may be embedded in query.",
                "default": "",
            },
        },
        "required": ["query"],
    }

    def __init__(self, repo_root: Path | str) -> None:
        self.repo_root = Path(repo_root)

    def execute(
        self,
        *,
        query: str,
        path: str = ".",
        symbol: str = "",
        func_name: str = "",
        **_,
    ) -> ToolResult:
        target = (self.repo_root / path).resolve(strict=False)
        if not is_path_safe(target, self.repo_root):
            return ToolResult(False, "", "path outside repo root")
        if not target.exists():
            return ToolResult(False, "", f"path not found: {path}")

        # Language check: only Python files are supported.
        if target.is_file() and target.suffix != ".py":
            return ToolResult(False, "", f"unsupported language: {target.suffix or '(none)'}")

        parts = query.strip().split(None, 1)
        verb = parts[0].lower() if parts else ""
        embedded_arg = parts[1] if len(parts) > 1 else None

        try:
            if verb == "definitions":
                return self._definitions(target)
            if verb == "references":
                arg = symbol or embedded_arg
                if not arg:
                    return ToolResult(False, "", "references requires a symbol")
                return self._references(target, arg)
            if verb == "callees":
                arg = func_name or embedded_arg
                if not arg:
                    return ToolResult(False, "", "callees requires a function name")
                return self._callees(target, arg)
            return ToolResult(False, "", f"unknown query verb: {verb!r}")
        except SyntaxError as e:
            return ToolResult(False, "", f"python syntax error: {e}")

    # ---- queries -----------------------------------------------------------

    def _definitions(self, target: Path) -> ToolResult:
        lines: list[str] = []
        for py in self._iter_python(target):
            try:
                tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"), filename=str(py))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    kind = "class" if isinstance(node, ast.ClassDef) else "def"
                    rel = py.relative_to(self.repo_root).as_posix()
                    lines.append(f"{rel}:{node.lineno} {kind} {node.name}")
        return ToolResult(True, "\n".join(lines) if lines else "(no definitions)")

    def _references(self, target: Path, symbol: str) -> ToolResult:
        # Use ripgrep to find candidate lines, then validate with ast that the
        # match is an actual Name node in load/store context.
        candidates: list[str] = []
        pattern = rf"\b{re.escape(symbol)}\b"
        for py in self._iter_python(target):
            try:
                text = py.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text, filename=str(py))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == symbol:
                    candidates.append(f"{py.relative_to(self.repo_root).as_posix()}:{node.lineno}")
                elif isinstance(node, ast.Attribute) and node.attr == symbol:
                    candidates.append(f"{py.relative_to(self.repo_root).as_posix()}:{node.lineno}")
        # Also use ripgrep to catch docstrings/comments if pattern is simple alphanumeric.
        if symbol.replace("_", "").isalnum():
            try:
                out = subprocess.run(
                    ["rg", "-n", "--no-heading", pattern, str(target)],
                    capture_output=True, text=True, timeout=10, check=False,
                )
                for line in out.stdout.splitlines():
                    file_part = line.split(":", 2)[0]
                    try:
                        if Path(file_part).resolve().is_relative_to(self.repo_root):
                            candidates.append(line)
                    except (OSError, ValueError):
                        continue
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass  # ripgrep unavailable; AST pass still ran
        # Deduplicate while preserving order.
        seen = set()
        unique = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return ToolResult(True, "\n".join(unique) if unique else f"(no references to {symbol})")

    def _callees(self, target: Path, func_name: str) -> ToolResult:
        # If target is a directory, search recursively for the function.
        if target.is_file():
            files = [target]
        else:
            files = list(self._iter_python(target))
        lines: list[str] = []
        for py in files:
            try:
                tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"), filename=str(py))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                    calls = set()
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Call):
                            name = self._call_name(sub.func)
                            if name:
                                calls.add(name)
                    rel = py.relative_to(self.repo_root).as_posix()
                    lines.append(f"{rel}:{node.lineno} {func_name}() calls: {sorted(calls)}")
        return ToolResult(True, "\n".join(lines) if lines else f"(function {func_name} not found)")

    @staticmethod
    def _call_name(func: ast.AST) -> str | None:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return None

    def _iter_python(self, target: Path):
        if target.is_file():
            if target.suffix == ".py":
                yield target
            else:
                return
        else:
            for p in target.rglob("*.py"):
                # Skip .venv, .git, node_modules.
                parts = set(p.parts)
                if parts & {".venv", ".git", "node_modules", "__pycache__"}:
                    continue
                yield p