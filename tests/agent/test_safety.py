from pathlib import Path

import pytest

from biz.agent.safety import (
    is_path_safe,
    is_sensitive_path,
    SENSITIVE_PATH_PATTERNS,
)


class TestIsPathSafe:
    def test_within_repo(self, tmp_path: Path):
        repo = tmp_path
        f = repo / "src" / "main.py"
        f.parent.mkdir()
        f.write_text("x")
        assert is_path_safe(f, repo) is True

    def test_escape_via_dotdot(self, tmp_path: Path):
        repo = tmp_path / "repo"
        repo.mkdir()
        outside = tmp_path / "secret.txt"
        outside.write_text("x")
        escape = repo / ".." / "secret.txt"
        assert is_path_safe(escape, repo) is False

    def test_absolute_outside(self, tmp_path: Path):
        repo = tmp_path / "repo"
        repo.mkdir()
        assert is_path_safe(Path("/etc/passwd"), repo) is False

    def test_exact_repo_root_is_safe(self, tmp_path: Path):
        repo = tmp_path / "repo"
        repo.mkdir()
        assert is_path_safe(repo, repo) is True


class TestIsSensitivePath:
    @pytest.mark.parametrize("path", [
        ".env",
        ".env.local",
        "src/.env",
        "id_rsa",
        "keys/id_rsa",
        "certs/server.pem",
        ".git/config",
        ".git/HEAD",
    ])
    def test_sensitive(self, tmp_path: Path, path):
        f = tmp_path / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
        assert is_sensitive_path(f) is True

    @pytest.mark.parametrize("path", [
        "src/main.py",
        "README.md",
        "tests/test_main.py",
    ])
    def test_not_sensitive(self, tmp_path: Path, path):
        f = tmp_path / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
        assert is_sensitive_path(f) is False
