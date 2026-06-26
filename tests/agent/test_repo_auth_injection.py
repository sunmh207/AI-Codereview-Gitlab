"""Tests for host-based credential injection in LocalRepoSyncer.

Covers:
  - _pick_token_for_host: env-var selection by host pattern
  - _auth_url: URL rewriting / no-op rules / URL-encoding
  - _ensure_authenticated_remote: rewriting the cached repo's origin URL
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from biz.agent.repo_syncer import (
    LocalRepoSyncer,
    _auth_url,
    _pick_token_for_host,
)


# --------------------------------------------------------------------------- #
# _pick_token_for_host
# --------------------------------------------------------------------------- #


class TestPickTokenForHost:
    def test_github_com_uses_github_token(self, monkeypatch):
        monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "gh_tok")
        monkeypatch.setenv("GITLAB_ACCESS_TOKEN", "gl_tok")
        assert _pick_token_for_host("github.com") == "gh_tok"

    def test_github_enterprise_subdomain_uses_github_token(self, monkeypatch):
        monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "gh_tok")
        monkeypatch.setenv("GITLAB_ACCESS_TOKEN", "gl_tok")
        assert _pick_token_for_host("api.github.com") == "gh_tok"

    def test_non_github_domain_with_github_substring_falls_back(self, monkeypatch):
        # "github.evil.com" must NOT match — only github.com / *.github.com.
        monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "gh_tok")
        monkeypatch.setenv("GITLAB_ACCESS_TOKEN", "gl_tok")
        assert _pick_token_for_host("github.evil.com") == "gl_tok"

    def test_gitea_host_uses_gitea_token(self, monkeypatch):
        monkeypatch.setenv("GITEA_ACCESS_TOKEN", "gt_tok")
        monkeypatch.setenv("GITLAB_ACCESS_TOKEN", "gl_tok")
        assert _pick_token_for_host("gitea.example.com") == "gt_tok"

    def test_non_gitea_substring_falls_back_to_gitlab(self, monkeypatch):
        monkeypatch.setenv("GITEA_ACCESS_TOKEN", "gt_tok")
        monkeypatch.setenv("GITLAB_ACCESS_TOKEN", "gl_tok")
        assert _pick_token_for_host("coding.codeages.work") == "gl_tok"

    def test_self_hosted_gitlab_uses_gitlab_token(self, monkeypatch):
        monkeypatch.setenv("GITLAB_ACCESS_TOKEN", "gl_tok")
        assert _pick_token_for_host("gitlab.example.com") == "gl_tok"

    def test_empty_host_returns_none(self, monkeypatch):
        monkeypatch.setenv("GITLAB_ACCESS_TOKEN", "gl_tok")
        assert _pick_token_for_host("") is None
        assert _pick_token_for_host(None) is None

    def test_unset_token_returns_none(self, monkeypatch):
        monkeypatch.delenv("GITLAB_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("GITEA_ACCESS_TOKEN", raising=False)
        assert _pick_token_for_host("github.com") is None
        assert _pick_token_for_host("coding.codeages.work") is None


# --------------------------------------------------------------------------- #
# _auth_url
# --------------------------------------------------------------------------- #


class TestAuthUrl:
    def test_injects_github_token_for_github(self, monkeypatch):
        monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "gh_tok")
        out = _auth_url("https://github.com/owner/repo.git")
        assert out == "https://oauth2:gh_tok@github.com/owner/repo.git"

    def test_injects_gitlab_token_for_self_hosted(self, monkeypatch):
        monkeypatch.setenv("GITLAB_ACCESS_TOKEN", "gl_tok")
        out = _auth_url("https://coding.codeages.work/he/devops/aicodereview.git")
        assert out == "https://oauth2:gl_tok@coding.codeages.work/he/devops/aicodereview.git"

    def test_injects_gitea_token(self, monkeypatch):
        monkeypatch.setenv("GITEA_ACCESS_TOKEN", "gt_tok")
        out = _auth_url("https://gitea.example.com/owner/repo.git")
        assert out == "https://oauth2:gt_tok@gitea.example.com/owner/repo.git"

    def test_token_with_special_chars_is_url_encoded(self, monkeypatch):
        # `+`, `/`, `=` are reserved; `@` would shift the netloc.
        monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "abc+def/ghi=jkl@mno")
        out = _auth_url("https://github.com/owner/repo.git")
        assert out == "https://oauth2:abc%2Bdef%2Fghi%3Djkl%40mno@github.com/owner/repo.git"

    def test_already_credentialed_url_unchanged(self, monkeypatch):
        monkeypatch.setenv("GITLAB_ACCESS_TOKEN", "gl_tok")
        original = "https://user:existing@gitlab.com/owner/repo.git"
        assert _auth_url(original) == original

    def test_ssh_url_unchanged(self, monkeypatch):
        monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "gh_tok")
        assert _auth_url("git@github.com:owner/repo.git") == "git@github.com:owner/repo.git"

    def test_local_file_path_unchanged(self, monkeypatch):
        monkeypatch.setenv("GITLAB_ACCESS_TOKEN", "gl_tok")
        assert _auth_url("/var/repos/foo.git") == "/var/repos/foo.git"

    def test_no_token_returns_url_unchanged(self, monkeypatch):
        monkeypatch.delenv("GITLAB_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("GITEA_ACCESS_TOKEN", raising=False)
        assert _auth_url("https://coding.codeages.work/he/proj.git") == \
            "https://coding.codeages.work/he/proj.git"

    def test_url_with_port_preserves_port(self, monkeypatch):
        monkeypatch.setenv("GITLAB_ACCESS_TOKEN", "gl_tok")
        out = _auth_url("https://gitlab.example.com:8443/owner/repo.git")
        assert out == "https://oauth2:gl_tok@gitlab.example.com:8443/owner/repo.git"

    def test_empty_token_string_treated_as_unset(self, monkeypatch):
        monkeypatch.setenv("GITLAB_ACCESS_TOKEN", "")
        assert _auth_url("https://coding.codeages.work/he/proj.git") == \
            "https://coding.codeages.work/he/proj.git"


# --------------------------------------------------------------------------- #
# _ensure_authenticated_remote
# --------------------------------------------------------------------------- #


@pytest.fixture
def bare_remote(tmp_path: Path) -> Path:
    """Create a local bare git repo with one initial commit on `main`."""
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


@pytest.fixture
def cached_repo_with_bare_origin(tmp_path: Path, bare_remote: Path) -> Path:
    """A working tree cloned from bare_remote, with a credential-free HTTPS
    origin URL. We rewrite the origin to a fake HTTPS URL after the clone
    so the auth-injection logic actually has an HTTP URL to rewrite.
    """
    work = tmp_path / "cache" / "proj"
    work.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "-q", str(bare_remote), str(work)],
        check=True,
    )
    # Set origin to a plain HTTPS URL (no creds). The remote doesn't need
    # to be reachable — we only test local URL manipulation.
    subprocess.run(
        ["git", "remote", "set-url", "origin", "https://coding.example.com/group/proj.git"],
        cwd=work, check=True, capture_output=True,
    )
    r = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=work, check=True, capture_output=True, text=True,
    )
    assert "@" not in r.stdout  # no creds
    return work


class TestEnsureAuthenticatedRemote:
    def test_rewrites_origin_when_token_available(
        self, tmp_path, cached_repo_with_bare_origin: Path
    ):
        syncer = LocalRepoSyncer(cache_root=tmp_path / "cache")

        with patch(
            "biz.agent.repo_syncer._pick_token_for_host",
            return_value="fake_token_123",
        ):
            syncer._ensure_authenticated_remote(cached_repo_with_bare_origin)

        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cached_repo_with_bare_origin, check=True, capture_output=True, text=True,
        )
        new_url = r.stdout.strip()
        assert new_url == "https://oauth2:fake_token_123@coding.example.com/group/proj.git"

    def test_noop_when_token_unavailable(
        self, tmp_path, cached_repo_with_bare_origin: Path
    ):
        syncer = LocalRepoSyncer(cache_root=tmp_path / "cache")
        original_url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cached_repo_with_bare_origin, check=True, capture_output=True, text=True,
        ).stdout.strip()

        with patch(
            "biz.agent.repo_syncer._pick_token_for_host",
            return_value=None,
        ):
            syncer._ensure_authenticated_remote(cached_repo_with_bare_origin)

        after = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cached_repo_with_bare_origin, check=True, capture_output=True, text=True,
        ).stdout.strip()
        assert after == original_url

    def test_noop_when_origin_already_credentialed(
        self, tmp_path, cached_repo_with_bare_origin: Path
    ):
        # Pre-set the origin to an already-credentialed URL.
        cred_url = "https://user:preexisting@somewhere.example/proj.git"
        subprocess.run(
            ["git", "remote", "set-url", "origin", cred_url],
            cwd=cached_repo_with_bare_origin, check=True, capture_output=True,
        )

        syncer = LocalRepoSyncer(cache_root=tmp_path / "cache")
        with patch(
            "biz.agent.repo_syncer._pick_token_for_host",
            return_value="some_token",
        ):
            syncer._ensure_authenticated_remote(cached_repo_with_bare_origin)

        after = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cached_repo_with_bare_origin, check=True, capture_output=True, text=True,
        ).stdout.strip()
        assert after == cred_url

    def test_noop_when_no_origin(self, tmp_path):
        # A dir with .git but no remote.
        work = tmp_path / "no_origin"
        work.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=work, check=True)
        # No `git remote add` — origin doesn't exist.
        syncer = LocalRepoSyncer(cache_root=tmp_path / "cache")
        # Should not raise.
        syncer._ensure_authenticated_remote(work)
