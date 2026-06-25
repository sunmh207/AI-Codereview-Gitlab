"""run_command tool: sandboxed shell execution within the repo."""
from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

from biz.agent.safety import is_path_safe, is_sensitive_path
from biz.agent.tool import Tool, ToolResult

# Default allowlist (first token of cmd must be in this set, or start with these).
DEFAULT_ALLOWLIST: list[str] = [
    "ls", "cat", "head", "tail", "find", "rg", "grep", "wc",
    "tree", "file", "stat", "diff",
    "git",       # further restricted to safe subcommands below
    "echo", "pwd", "true", "false",
]

# Safe git subcommands (matched as: cmd starts with `git <subcommand>`).
SAFE_GIT_SUBCOMMANDS = {
    "log", "show", "diff", "blame", "ls-files", "ls-tree", "status",
}

# Default blocklist (takes precedence over allowlist).
DEFAULT_BLOCKLIST: list[str] = [
    "rm", "mv", "cp", "chmod", "chown", "sudo",
    "curl", "wget", "ssh", "scp", "rsync",
    "dd", "mkfs", "mount", "umount",
    "kubectl", "docker", "podman",
    "npm", "yarn", "pnpm", "pip", "pip3", "easy_install",
    "bash", "sh", "zsh", "fish",   # no nested shells
    "python", "python3", "ruby", "perl", "node",  # code execution paths
]

# Regex patterns that flag path traversal in commands.
_TRAVERSAL_PATTERNS = [
    re.compile(r"\.\./"),
    re.compile(r"\.\.$"),
    re.compile(r"/\.\."),  # /..
]

# Absolute-path regex (POSIX).
_ABS_PATH_RE = re.compile(r"(?:^|[\s|>])(/[A-Za-z0-9_\-.]+)")


class RunCommandTool(Tool):
    name = "run_command"
    description = (
        "Run a shell command in the repository root. Sandboxed: only read-only "
        "commands are allowed; the working directory is fixed to the repo root; "
        "paths outside the repo and sensitive files are blocked. Output is "
        "truncated if large."
    )
    parameters = {
        "type": "object",
        "properties": {
            "cmd": {"type": "string", "description": "Shell command to execute."},
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds.",
                "default": 30,
                "minimum": 1,
                "maximum": 300,
            },
        },
        "required": ["cmd"],
    }

    def __init__(
        self,
        repo_root: Path | str,
        *,
        allowlist: list[str] | None = None,
        blocklist: list[str] | None = None,
        timeout: int = 30,
    ) -> None:
        self.repo_root = Path(repo_root).resolve(strict=False)
        self.allowlist = set(allowlist if allowlist is not None else DEFAULT_ALLOWLIST)
        self.blocklist = set(blocklist if blocklist is not None else DEFAULT_BLOCKLIST)
        self.timeout = timeout

    def execute(self, *, cmd: str, timeout: int | None = None, **_) -> ToolResult:
        cmd = cmd.strip()
        if not cmd:
            return ToolResult(False, "", "empty command")

        # ---- pre-checks ----
        # Path traversal (textual).
        if any(p.search(cmd) for p in _TRAVERSAL_PATTERNS):
            return ToolResult(False, "", "path outside repo: command rejected")

        # Absolute outside-repo paths.
        for m in _ABS_PATH_RE.finditer(cmd):
            abs_path = m.group(1)
            candidate = Path(abs_path)
            if not is_path_safe(candidate, self.repo_root):
                return ToolResult(False, "", f"path outside repo: {abs_path}")

        # Sensitive path mentions.
        for token in shlex.split(cmd, posix=True):
            # Tokens that look like paths.
            if "/" in token or token.startswith("."):
                p = (self.repo_root / token).resolve(strict=False) if not token.startswith("/") else Path(token)
                if is_sensitive_path(p):
                    return ToolResult(False, "", f"sensitive path: {token}")

        # Tokenize for first-command check.
        try:
            tokens = shlex.split(cmd, posix=True)
        except ValueError as e:
            return ToolResult(False, "", f"parse error: {e}")
        if not tokens:
            return ToolResult(False, "", "no tokens parsed")
        head = tokens[0]

        # Blocklist wins.
        if head in self.blocklist:
            return ToolResult(False, "", f"command blocked by sandbox: {head}")
        # Allowlist required.
        if head not in self.allowlist:
            return ToolResult(False, "", f"command not allowed: {head}")

        # Git subcommand allowlist.
        if head == "git":
            if len(tokens) < 2 or tokens[1] not in SAFE_GIT_SUBCOMMANDS:
                return ToolResult(False, "", f"git subcommand not allowed: {tokens[1:]!r}")

        # ---- execute ----
        actual_timeout = int(timeout) if timeout else self.timeout
        try:
            completed = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.repo_root),
                timeout=actual_timeout,
                capture_output=True,
                text=True,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(False, "", f"command timed out after {actual_timeout}s")
        except Exception as e:
            return ToolResult(False, "", f"execution error: {type(e).__name__}: {e}")

        if completed.returncode != 0:
            err = completed.stderr.strip()[:2000] or f"exit code {completed.returncode}"
            return ToolResult(False, "", err)
        return ToolResult(True, completed.stdout)