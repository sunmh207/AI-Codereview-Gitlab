import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a minimal local git repository for testing.

    Returns the repo root path. Repo contains:
      - src/main.py
      - src/util.py
      - tests/test_main.py
      - README.md
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "tests").mkdir()
    (repo / "src" / "main.py").write_text(
        "def greet(name):\n"
        "    return f'hello {name}'\n"
        "\n"
        "def main():\n"
        "    print(greet('world'))\n"
    )
    (repo / "src" / "util.py").write_text(
        "def add(a, b):\n"
        "    return a + b\n"
    )
    (repo / "tests" / "test_main.py").write_text(
        "from src.main import greet\n"
        "\n"
        "def test_greet():\n"
        "    assert greet('x') == 'hello x'\n"
    )
    (repo / "README.md").write_text("# test repo\n")

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "[email protected]"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    return repo


@pytest.fixture
def mock_llm_response():
    """Factory for building fake LLMResponse objects."""

    def _make(content=None, tool_calls=None, raw=None):
        from biz.agent.llm_adapter import LLMResponse, ToolCall

        return LLMResponse(content=content, tool_calls=tool_calls or [], raw=raw)

    return _make
