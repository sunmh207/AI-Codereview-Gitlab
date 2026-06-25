from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from biz.agent.agentic_reviewer import AgenticReviewer
from biz.agent.llm_adapter import LLMResponse, ToolCall
from biz.utils.code_reviewer import CodeReviewer


def _fake_remote(tmp_path: Path) -> Path:
    import subprocess
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


class TestAgenticReviewer:
    def test_review_returns_llm_content(self, tmp_path, monkeypatch):
        remote = _fake_remote(tmp_path)
        cache = tmp_path / "cache"

        # Mock the LLM client to return a fixed review.
        mock_client = MagicMock()
        mock_client.chat_with_tools.return_value = {
            "content": "Looks good. 总分:90分",
            "tool_calls": [],
            "raw": None,
        }
        from biz.agent.llm_adapter import LLMAdapter
        adapter = LLMAdapter(mock_client, use_native=True)

        reviewer = AgenticReviewer(
            repo_url=str(remote),
            repo_key="test/proj",
            ref="main",
            cache_root=cache,
            adapter=adapter,
            max_iterations=5,
        )
        result = reviewer.review(diffs_text="diff content", commits_text="msg")
        assert "Looks good" in result

    def test_review_degrades_when_output_missing_score_marker(self, tmp_path, monkeypatch):
        """Defense-in-depth: if the agent emits text that doesn't contain a
        `总分:XX分` marker (e.g. its own tool-selection reasoning leaked out),
        fall back to diff_only rather than posting the garbage as a review.

        Regression: PHP push events produced
        "The AST query doesn't find references, but the files do exist. Let me
        check the openspec folder for the design docs." — which is the agent
        thinking out loud, not a code review.
        """
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        remote = _fake_remote(tmp_path)
        cache = tmp_path / "cache"

        # LLM emits a "thinking out loud" string with no review format.
        mock_client = MagicMock()
        mock_client.chat_with_tools.return_value = {
            "content": (
                "The AST query doesn't find references, but the files do exist. "
                "Let me check the openspec folder for the design docs."
            ),
            "tool_calls": [],
            "raw": None,
        }
        from biz.agent.llm_adapter import LLMAdapter
        adapter = LLMAdapter(mock_client, use_native=True)

        with patch.object(
            CodeReviewer, "review_and_strip_code", return_value="FALLBACK REVIEW 总分:50分"
        ) as m:
            reviewer = AgenticReviewer(
                repo_url=str(remote),
                repo_key="test/proj_noreview",
                ref="main",
                cache_root=cache,
                adapter=adapter,
                max_iterations=3,
            )
            result = reviewer.review(diffs_text="d", commits_text="c")

        # Must not leak the agent's internal monologue.
        assert "openspec" not in result
        # Must have invoked the diff_only fallback.
        assert "FALLBACK" in result
        assert "50" in result
        m.assert_called_once()

    def test_review_soft_degrades_to_diff_only_on_runner_failure(self, tmp_path, monkeypatch):
        # Use a provider that doesn't require API keys for the soft-degrade path.
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        remote = _fake_remote(tmp_path)
        cache = tmp_path / "cache"

        # Make the runner raise.
        from biz.agent.runner import TokenBudgetExceeded

        mock_client = MagicMock()
        mock_client.chat_with_tools.return_value = {
            "content": None,
            "tool_calls": [{"id": "1", "name": "counter", "arguments": {"n": 1}}],
            "raw": None,
        }
        from biz.agent.llm_adapter import LLMAdapter
        adapter = LLMAdapter(mock_client, use_native=True)

        # Patch AgentRunner.run to raise.
        with patch("biz.agent.agentic_reviewer.AgentRunner") as MockRunner:
            mock_instance = MagicMock()
            mock_instance.run.side_effect = TokenBudgetExceeded("too big")
            MockRunner.return_value = mock_instance

            # Patch CodeReviewer to verify degradation runs it.
            with patch.object(CodeReviewer, "review_and_strip_code", return_value="FALLBACK REVIEW") as m:
                reviewer = AgenticReviewer(
                    repo_url=str(remote),
                    repo_key="test/proj2",
                    ref="main",
                    cache_root=cache,
                    adapter=adapter,
                    max_iterations=5,
                )
                result = reviewer.review(diffs_text="d", commits_text="c")
                assert result == "FALLBACK REVIEW"
                m.assert_called_once()