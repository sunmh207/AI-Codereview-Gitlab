"""Top-level entry point for agentic review, used by worker.py."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from biz.agent.llm_adapter import LLMAdapter
from biz.agent.prompts import load_prompt
from biz.agent.repo_syncer import LocalRepoSyncer
from biz.agent.runner import AgentRunner
from biz.agent.tools import register_default_tools
from biz.agent.tool_registry import ToolRegistry
from biz.llm.factory import Factory
from biz.utils.code_reviewer import CodeReviewer
from biz.utils.log import logger
from biz.utils.im import notifier


def _slugify_repo_key(provider: str, project: str) -> str:
    """Build a stable cache key for a project."""
    return f"{provider}_{project}".replace("/", "_").replace(" ", "_")


def _parse_csv_env(name: str, default: list[str]) -> list[str]:
    """Read a comma-separated env var, fall back to `default` if unset/empty."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()] or list(default)


class AgenticReviewer:
    def __init__(
        self,
        *,
        repo_url: str,
        repo_key: str,
        ref: str,
        cache_root: Path | str,
        adapter: LLMAdapter | None = None,
        max_iterations: int = 20,
        total_token_cap: int = 80_000,
    ) -> None:
        self.repo_url = repo_url
        self.repo_key = repo_key
        self.ref = ref
        self.cache_root = Path(cache_root)
        self.adapter = adapter
        self.max_iterations = max_iterations
        self.total_token_cap = total_token_cap

    def _build_adapter(self) -> LLMAdapter:
        if self.adapter is not None:
            return self.adapter
        client = Factory().getClient()
        return LLMAdapter(client)

    def _build_registry(self, repo_root: Path) -> ToolRegistry:
        registry = ToolRegistry()
        from biz.agent.tools.run_command import (
            DEFAULT_ALLOWLIST,
            DEFAULT_BLOCKLIST,
        )
        allow = _parse_csv_env("AGENT_SHELL_ALLOWLIST", DEFAULT_ALLOWLIST)
        block = _parse_csv_env("AGENT_SHELL_BLOCKLIST", DEFAULT_BLOCKLIST)
        register_default_tools(registry, repo_root, allowlist=allow, blocklist=block)
        return registry

    def review(self, diffs_text: str, commits_text: str) -> str:
        # 1. Sync repo locally.
        try:
            syncer = LocalRepoSyncer(cache_root=self.cache_root)
            repo_root = syncer.sync_to(url=self.repo_url, key=self.repo_key, ref=self.ref)
        except Exception as e:
            logger.error("agentic repo sync failed, degrading: %s", e)
            notifier.send_notification(content=f"[agentic] repo sync failed: {e}; falling back to diff_only")
            return CodeReviewer().review_and_strip_code(diffs_text, commits_text)

        # 2. Build adapter, registry, runner.
        adapter = self._build_adapter()
        registry = self._build_registry(repo_root)
        runner = AgentRunner(
            adapter=adapter,
            registry=registry,
            max_iterations=self.max_iterations,
            total_token_cap=self.total_token_cap,
        )

        # 3. Build initial messages from prompt template.
        prompts = load_prompt("agentic_code_review_prompt", style=os.getenv("REVIEW_STYLE", "professional"))
        user_content = prompts["user_message"]["content"].format(
            diffs_text=diffs_text,
            commits_text=commits_text,
            repo_root=str(repo_root),
        )
        messages = [prompts["system_message"], {"role": "user", "content": user_content}]

        # 4. Run the agent loop with soft-degrade.
        try:
            return runner.run(messages)
        except Exception as e:
            logger.error("agentic run failed, degrading to diff_only: %s", e)
            notifier.send_notification(content=f"[agentic] run failed: {e}; falling back to diff_only")
            return CodeReviewer().review_and_strip_code(diffs_text, commits_text)