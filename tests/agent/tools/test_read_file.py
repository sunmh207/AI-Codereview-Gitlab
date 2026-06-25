import pytest

from biz.agent.safety import SENSITIVE_PATH_PATTERNS  # noqa: F401  ensure import
from biz.agent.tools.read_file import ReadFileTool


@pytest.fixture
def repo_with_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "main.py").write_text(
        "line1\nline2\nline3\nline4\nline5\n"
    )
    (repo / ".env").write_text("SECRET=x\n")
    binary = repo / "blob.bin"
    binary.write_bytes(b"\x00\x01\x00\x02\x00\x03")
    return repo


class TestReadFile:
    def test_read_full_file_default(self, repo_with_files):
        t = ReadFileTool(repo_with_files)
        r = t.execute(path="src/main.py")
        assert r.success is True
        assert "line1" in r.output
        assert "line5" in r.output

    def test_read_with_offset_and_limit(self, repo_with_files):
        t = ReadFileTool(repo_with_files)
        r = t.execute(path="src/main.py", offset=2, limit=2)
        assert r.success is True
        # Format: "lines N-M:\n<content>"
        assert "line3" in r.output
        assert "line4" in r.output
        assert "line5" not in r.output

    def test_path_outside_repo_rejected(self, repo_with_files):
        t = ReadFileTool(repo_with_files)
        r = t.execute(path="../escape.txt")
        assert r.success is False
        assert "outside repo" in (r.error or "").lower()

    def test_absolute_path_outside_repo_rejected(self, repo_with_files):
        t = ReadFileTool(repo_with_files)
        r = t.execute(path="/etc/passwd")
        assert r.success is False
        assert "outside repo" in (r.error or "").lower()

    def test_sensitive_path_rejected(self, repo_with_files):
        t = ReadFileTool(repo_with_files)
        r = t.execute(path=".env")
        assert r.success is False
        assert "sensitive" in (r.error or "").lower()

    def test_binary_file_rejected(self, repo_with_files):
        t = ReadFileTool(repo_with_files)
        r = t.execute(path="blob.bin")
        assert r.success is False
        assert "binary" in (r.error or "").lower()

    def test_missing_file(self, repo_with_files):
        t = ReadFileTool(repo_with_files)
        r = t.execute(path="nonexistent.py")
        assert r.success is False
        assert "not found" in (r.error or "").lower()

    def test_to_schema_has_path_param(self, repo_with_files):
        t = ReadFileTool(repo_with_files)
        s = t.to_schema()
        assert s["function"]["name"] == "read_file"
        assert "path" in s["function"]["parameters"]["properties"]
