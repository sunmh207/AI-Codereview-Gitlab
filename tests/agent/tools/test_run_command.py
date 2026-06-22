import os
import pytest

from biz.agent.tools.run_command import RunCommandTool


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("alpha\n")
    (repo / ".env").write_text("SECRET=x\n")
    return repo


def _tool(repo, **overrides):
    """Build a tool with permissive defaults unless overridden."""
    defaults = dict(
        allowlist=["ls", "cat", "echo", "rg", "grep", "find"],
        blocklist=["rm", "curl"],
        timeout=5,
    )
    defaults.update(overrides)
    return RunCommandTool(repo, **defaults)


class TestRunCommand:
    def test_allowlisted_command_runs(self, repo):
        t = _tool(repo)
        r = t.execute(cmd="cat a.txt")
        assert r.success is True
        assert "alpha" in r.output

    def test_blocklisted_command_rejected(self, repo):
        t = _tool(repo)
        r = t.execute(cmd="rm -rf .")
        assert r.success is False
        assert "blocked" in (r.error or "").lower()

    def test_blocklist_takes_precedence_over_allowlist(self, repo):
        t = _tool(repo, allowlist=["rm"], blocklist=["rm"])
        r = t.execute(cmd="rm -rf .")
        assert r.success is False
        assert "blocked" in (r.error or "").lower()

    def test_unknown_command_rejected(self, repo):
        t = _tool(repo)
        r = t.execute(cmd="evil_binary --flag")
        assert r.success is False
        assert "not allowed" in (r.error or "").lower()

    def test_path_traversal_rejected(self, repo):
        t = _tool(repo)
        r = t.execute(cmd="cat ../escape.txt")
        assert r.success is False
        assert "outside" in (r.error or "").lower()

    def test_absolute_outside_path_rejected(self, repo):
        t = _tool(repo)
        r = t.execute(cmd="cat /etc/passwd")
        assert r.success is False
        assert "outside" in (r.error or "").lower()

    def test_sensitive_path_rejected(self, repo):
        t = _tool(repo)
        r = t.execute(cmd="cat .env")
        assert r.success is False
        assert "sensitive" in (r.error or "").lower()

    def test_timeout_returns_error(self, repo):
        t = _tool(repo, allowlist=["sleep"], timeout=1)
        r = t.execute(cmd="sleep 5")
        assert r.success is False
        assert "timed out" in (r.error or "").lower()

    def test_nonzero_exit_returns_error_with_stderr(self, repo):
        t = _tool(repo, allowlist=["false"])
        r = t.execute(cmd="false")
        assert r.success is False
        # exit code may be referenced in error string
        assert "exit" in (r.error or "").lower() or "false" in (r.error or "").lower()

    def test_to_schema(self, repo):
        t = _tool(repo)
        s = t.to_schema()
        assert s["function"]["name"] == "run_command"
        assert "cmd" in s["function"]["parameters"]["properties"]