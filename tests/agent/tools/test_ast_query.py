import textwrap

import pytest

from biz.agent.tools.ast_query import ASTQueryTool


@pytest.fixture
def python_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text(textwrap.dedent("""
        from util import add

        def greet(name):
            return f"hi {name}"

        def main():
            print(greet("world"))
            print(add(1, 2))
    """))
    (repo / "util.py").write_text(textwrap.dedent("""
        def add(a, b):
            return a + b

        class Calculator:
            def multiply(self, x, y):
                return x * y
    """))
    return repo


class TestASTQuery:
    def test_definitions_lists_functions_and_classes(self, python_repo):
        t = ASTQueryTool(python_repo)
        r = t.execute(query="definitions", path=".")
        assert r.success is True
        assert "greet" in r.output
        assert "main" in r.output
        assert "Calculator" in r.output

    def test_definitions_single_file(self, python_repo):
        t = ASTQueryTool(python_repo)
        r = t.execute(query="definitions", path="util.py")
        assert r.success is True
        assert "add" in r.output
        assert "multiply" in r.output

    def test_references_finds_usages(self, python_repo):
        t = ASTQueryTool(python_repo)
        r = t.execute(query="references", symbol="greet", path=".")
        assert r.success is True
        # greet is defined in app.py and called in main()
        assert "app.py" in r.output

    def test_callees_lists_calls_within_function(self, python_repo):
        t = ASTQueryTool(python_repo)
        r = t.execute(query="callees", func_name="main", path="app.py")
        assert r.success is True
        assert "print" in r.output
        assert "greet" in r.output

    def test_unknown_query_returns_error(self, python_repo):
        t = ASTQueryTool(python_repo)
        r = t.execute(query="wat", path=".")
        assert r.success is False
        assert "unknown query" in (r.error or "").lower()

    def test_non_python_file_returns_error(self, python_repo):
        (python_repo / "readme.txt").write_text("hi")
        t = ASTQueryTool(python_repo)
        r = t.execute(query="definitions", path="readme.txt")
        assert r.success is False
        assert "language" in (r.error or "").lower()

    def test_to_schema(self, python_repo):
        t = ASTQueryTool(python_repo)
        s = t.to_schema()
        assert s["function"]["name"] == "ast_query"