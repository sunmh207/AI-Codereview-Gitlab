#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 CodeReviewer 的功能，包括：
1. Jinja2模板在file_contents_text为空时不渲染文件内容部分
2. 文件内容超过token限制时的截断场景
"""
import os
from unittest import TestCase

from jinja2 import Template

from biz.utils.token_util import count_tokens, truncate_text_by_tokens


class TestCodeReviewer(TestCase):
    def setUp(self):
        """设置测试环境"""
        # 设置环境变量，避免依赖实际配置
        os.environ.setdefault("REVIEW_MAX_TOKENS", "1000")
        os.environ.setdefault("REVIEW_STYLE", "professional")

    def test_jinja2_template_without_file_contents(self):
        """测试Jinja2模板在file_contents_text为空时不渲染文件内容部分"""
        # 模拟user_prompt模板
        template_str = """以下是某位员工向 GitLab 代码库提交的代码，请以{{ style }}风格审查以下代码。

代码变更内容：
{{ diffs_text }}
{% if file_contents_text %}

修改后的文件内容（用于上下文参考）：
{{ file_contents_text }}
{% endif %}

提交历史(commits)：
{{ commits_text }}"""
        
        template = Template(template_str)
        
        # 测试1: file_contents_text为空字符串
        result_empty = template.render(
            style="professional",
            diffs_text="diff内容",
            commits_text="commit信息",
            file_contents_text=""
        )
        
        # 验证文件内容部分没有被渲染
        self.assertNotIn("修改后的文件内容", result_empty)
        self.assertIn("diff内容", result_empty)
        self.assertIn("commit信息", result_empty)
        
        # 测试2: file_contents_text为None（Jinja2会将None视为False）
        result_none = template.render(
            style="professional",
            diffs_text="diff内容",
            commits_text="commit信息",
            file_contents_text=None
        )
        
        # 验证文件内容部分没有被渲染
        self.assertNotIn("修改后的文件内容", result_none)
        
        # 测试3: file_contents_text有内容
        result_with_content = template.render(
            style="professional",
            diffs_text="diff内容",
            commits_text="commit信息",
            file_contents_text="文件内容测试"
        )
        
        # 验证文件内容部分被渲染了
        self.assertIn("修改后的文件内容", result_with_content)
        self.assertIn("文件内容测试", result_with_content)

    def test_file_contents_truncation_when_exceeds_tokens(self):
        """测试文件内容超过token限制时的截断场景"""
        # 设置较小的token限制用于测试
        review_max_tokens = 100
        
        # 创建一个较小的diff（占用少量tokens）
        small_diff = "diff line 1\ndiff line 2\n"
        diff_tokens = count_tokens(small_diff)
        
        # 创建一个较大的文件内容（会超过可用token限制）
        large_file_content = "x " * 1000  # 创建一个较大的文件内容
        file_tokens = count_tokens(large_file_content)
        
        # 确保文件内容确实超过了可用空间
        available_tokens = review_max_tokens - diff_tokens
        self.assertGreater(file_tokens, available_tokens, "文件内容应该超过可用token限制")
        
        # 模拟token截断逻辑
        processed_file_contents = {}
        remaining_tokens = available_tokens
        
        # 模拟添加文件内容的逻辑
        file_path = "test_file.py"
        content = large_file_content
        
        if file_tokens <= remaining_tokens:
            processed_file_contents[file_path] = content
        elif remaining_tokens > 0:
            # 截断文件内容
            processed_file_contents[file_path] = truncate_text_by_tokens(
                content, remaining_tokens
            )
        
        # 验证文件内容被截断了
        self.assertIn(file_path, processed_file_contents)
        truncated_content = processed_file_contents[file_path]
        truncated_tokens = count_tokens(truncated_content)
        
        # 验证截断后的token数不超过可用空间
        self.assertLessEqual(truncated_tokens, available_tokens, 
                           "文件内容应该被截断到可用token范围内")
        self.assertLess(len(truncated_content), len(large_file_content),
                       "截断后的内容应该比原始内容短")
      
    def test_file_contents_with_multiple_files(self):
        """测试多个文件时的token截断逻辑"""
        review_max_tokens = 200
        
        small_diff = "diff content\n"
        diff_tokens = count_tokens(small_diff)
        available_tokens = review_max_tokens - diff_tokens
        
        # 创建多个文件，确保场景：file1完整，file2截断，file3没有
        # file1: 较小的文件，可以完整添加
        file1_content = "x " * 30
        file1_tokens = count_tokens(file1_content)
        
        # file2: 较大的文件，会超过剩余空间，需要截断
        file2_content = "y " * 500  # 确保超过剩余空间
        file2_tokens = count_tokens(file2_content)
        
        # file3: 第三个文件，应该不会被添加（因为file2截断后会break）
        file3_content = "z " * 50
        
        # 确保file1可以完整添加，但file2会超过剩余空间
        self.assertLess(file1_tokens, available_tokens, "file1应该可以完整添加")
        self.assertGreater(file2_tokens, available_tokens - file1_tokens, 
                          "file2应该超过剩余空间，需要截断")
        
        file_contents = {
            "file1.py": file1_content,
            "file2.py": file2_content,
            "file3.py": file3_content,
        }
        
        # 模拟token截断逻辑
        processed_file_contents = {}
        remaining_tokens = available_tokens
        
        for file_path, content in file_contents.items():
            file_tokens = count_tokens(content)
            if file_tokens <= remaining_tokens:
                # 文件内容可以完整添加
                processed_file_contents[file_path] = content
                remaining_tokens -= file_tokens
            elif remaining_tokens > 0:
                # 文件内容超过剩余空间，截断后添加
                processed_file_contents[file_path] = truncate_text_by_tokens(
                    content, remaining_tokens
                )
                remaining_tokens = 0
                break
            else:
                # 没有剩余空间，跳过后续文件
                break
        
        # 验证file1完整添加
        self.assertIn("file1.py", processed_file_contents)
        self.assertEqual(processed_file_contents["file1.py"], file1_content)
        
        # 验证file2被截断
        self.assertIn("file2.py", processed_file_contents)
        self.assertLess(len(processed_file_contents["file2.py"]), len(file2_content))
        self.assertLess(count_tokens(processed_file_contents["file2.py"]), 
                       count_tokens(file2_content))
        
        # 验证file3没有被添加
        self.assertNotIn("file3.py", processed_file_contents)

    def test_review_code_with_empty_file_contents(self):
        """测试处理空文件内容的情况"""
        # 模拟格式化文件内容的逻辑
        file_contents = None
        file_contents_text = ""
        
        if file_contents:
            file_contents_list = []
            for file_path, content in file_contents.items():
                file_contents_list.append(
                    f"文件路径: {file_path}\n文件内容:\n```\n{content}\n```"
                )
            file_contents_text = "\n\n".join(file_contents_list)
        
        # 验证file_contents_text为空
        self.assertEqual(file_contents_text, "")
        
        # 使用模板渲染，验证空字符串不会渲染文件内容部分
        template_str = """以下是某位员工向 GitLab 代码库提交的代码，请以{{ style }}风格审查以下代码。

代码变更内容：
{{ diffs_text }}
{% if file_contents_text %}

修改后的文件内容（用于上下文参考）：
{{ file_contents_text }}
{% endif %}

提交历史(commits)：
{{ commits_text }}"""
        
        template = Template(template_str)
        result = template.render(
            style="professional",
            diffs_text="diff内容",
            commits_text="commit信息",
            file_contents_text=file_contents_text
        )
        
        # 验证文件内容部分没有被渲染
        self.assertNotIn("修改后的文件内容", result)
        self.assertIn("diff内容", result)
        self.assertIn("commit信息", result)

#python -m unittest biz.utils.test_code_reviewer -v
if __name__ == '__main__':
    import unittest
    unittest.main()

