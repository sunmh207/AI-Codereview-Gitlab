"""Soft-degrade tests for AgenticReviewer.

Verifies that AgenticReviewer falls back to CodeReviewer when:
  1. The repo sync step fails (bad remote URL).
  2. The AgentRunner raises an exception (e.g. TokenBudgetExceeded).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from biz.agent.agentic_reviewer import AgenticReviewer
from biz.agent.llm_adapter import LLMAdapter
from biz.agent.runner import TokenBudgetExceeded
from biz.utils.code_reviewer import CodeReviewer


@pytest.fixture
def bad_remote(tmp_path: Path) -> Path:
    """A path that does not exist (and never will)."""
    return tmp_path / "nonexistent.git"


@pytest.fixture
def tiny_remote(tmp_path: Path) -> Path:
    """Create a bare git remote with one initial commit on `main`."""
    remote = tmp_path / "remote.git"
    remote.mkdir()
    subprocess.run(["git", "init", "--bare", "-q"], cwd=remote, check=True)
    work = tmp_path / "work"
    work.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.email", "[email protected]"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=work, check=True)
    (work / "f.txt").write_text("v1\n")
    subprocess.run(["git", "add", "-A"], cwd=work, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "v1"], cwd=work, check=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=work, check=True)
    subprocess.run(["git", "push", "-q", "origin", "main"], cwd=work, check=True)
    return remote


class TestSoftDegrade:
    def test_repo_sync_failure_falls_back(self, tmp_path, bad_remote, monkeypatch):
        # CodeReviewer's __init__ calls Factory().getClient(); use ollama so it
        # doesn't require API keys. The patched review_and_strip_code short-
        # circuits any real network call anyway.
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        cache = tmp_path / "cache"
        adapter = LLMAdapter(MagicMock(), use_native=True)

        reviewer = AgenticReviewer(
            repo_url=str(bad_remote),
            repo_key="x",
            ref="main",
            cache_root=cache,
            adapter=adapter,
            max_iterations=3,
        )

        with patch.object(CodeReviewer, "review_and_strip_code", return_value="FALLBACK") as m:
            out = reviewer.review(diffs_text="d", commits_text="c")

        assert out == "FALLBACK"
        assert m.call_count == 1

    def test_runner_raises_falls_back(self, tmp_path, tiny_remote, monkeypatch):
        # Use a provider that doesn't require API keys for the soft-degrade path.
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        cache = tmp_path / "cache"

        adapter = LLMAdapter(MagicMock(), use_native=True)

        with patch("biz.agent.agentic_reviewer.AgentRunner") as MockRunner:
            inst = MagicMock()
            inst.run.side_effect = TokenBudgetExceeded("boom")
            MockRunner.return_value = inst

            reviewer = AgenticReviewer(
                repo_url=str(tiny_remote),
                repo_key="k",
                ref="main",
                cache_root=cache,
                adapter=adapter,
                max_iterations=3,
            )

            with patch.object(CodeReviewer, "review_and_strip_code", return_value="FALLBACK") as m:
                out = reviewer.review(diffs_text="d", commits_text="c")

        assert out == "FALLBACK"
        assert m.call_count == 1