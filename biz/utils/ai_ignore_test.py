import unittest

from biz.utils.ai_ignore import AIIgnore


class TestAIIgnore(unittest.TestCase):

    def test_is_ignored(self):
        # 测试用例
        test_cases = [
            # (规则列表, 测试路径, 预期结果)
            (["*.log"], "error.log", True),
            (["*.log"], "error.txt", False),
            (["*.log", "!important.log", ], "important.log", False),
            (["!important.log", "*.log"], "error.log", True),
            (["/config"], "config", True),
            (["/config"], "app/config", False),
            (["build/"], "build", True),
            (["build/"], "build/", True),
            (["build/"], "build/main.o", True),
            (["build/"], "src/build", False),
            (["doc/**/*.html"], "doc/index.html", True),
            (["doc/**/*.html"], "doc/manual/index.html", True),
            (["doc/**/*.html"], "docs/index.html", False),
            (["project[123]"], "project1", True),
            (["project[123]"], "project2", True),
            (["project[123]"], "project4", False),
            (["src/*.c"], "src/main.c", True),
            (["src/*.c"], "src/lib/utils.c", False),
            (["**/__pycache__/"], "app/__pycache__/", True),
            (["**/__pycache__/"], "app/utils/__pycache__/", True),
            (["!src/"], "src/main.c", False),  # 否定规则优先
        ]

        for i, (patterns, path, expected) in enumerate(test_cases):
            gitignore = AIIgnore(ai_ignore_content='\n'.join(patterns))
            result = gitignore.is_ignored(path)
            self.assertEqual(result, expected)
            print(f"\n测试用例 {i + 1}:")
            print(f"  规则: {patterns}")
            print(f"  路径: {path}")
            print(f"  预期结果: {expected}")
            print(f"  实际结果: {result}")
