import abc
import json
import os
import re
from typing import Dict, Any, List, Optional

import yaml
from jinja2 import Template

from biz.llm.factory import Factory
from biz.utils.config_loader import config_loader
from biz.utils.log import logger
from biz.utils.token_util import count_tokens, truncate_text_by_tokens


class BaseReviewer(abc.ABC):
    """代码审查基类"""

    def __init__(self, prompt_key: str, app_name: Optional[str] = None, project_path: Optional[str] = None, config: Optional[Dict[str, str]] = None):
        self.config = config or {}  # 项目专属配置
        self.client = Factory().getClient(config=self.config)
        self.app_name = app_name
        self.project_path = project_path
        # 从config中读取REVIEW_STYLE（已包含默认值）
        review_style = self.config.get("REVIEW_STYLE", "professional")
        self.prompts = self._load_prompts(prompt_key, review_style)

    def _load_prompts(self, prompt_key: str, style="professional") -> Dict[str, Any]:
        """加载提示词配置"""
        try:
            # 使用ConfigLoader加载Prompt模板
            prompts: dict[Any, Any] = config_loader.load_prompt_template(prompt_key, self.app_name, self.project_path)

            # 使用Jinja2渲染模板
            def render_template(template_str: str) -> str:
                return Template(template_str).render(style=style)

            system_prompt = render_template(prompts["system_prompt"])
            user_prompt = render_template(prompts["user_prompt"])

            return {
                "system_message": {"role": "system", "content": system_prompt},
                "user_message": {"role": "user", "content": user_prompt},
            }
        except (FileNotFoundError, KeyError, yaml.YAMLError) as e:
            logger.error(f"加载提示词配置失败: {e}")
            raise Exception(f"提示词配置加载失败: {e}")

    def call_llm(self, messages: List[Dict[str, Any]]) -> str:
        """调用 LLM 进行代码审核"""
        logger.info(f"向 AI 发送代码 Review 请求, messages: {messages}")
        review_result = self.client.completions(messages=messages)
        logger.info(f"收到 AI 返回结果: {review_result}")
        return review_result

    @abc.abstractmethod
    def review_code(self, *args, **kwargs) -> str:
        """抽象方法，子类必须实现"""
        pass


class CodeReviewer(BaseReviewer):
    """代码 Diff 级别的审查"""

    def __init__(self, app_name: Optional[str] = None, project_path: Optional[str] = None, config: Optional[Dict[str, str]] = None):
        super().__init__("code_review_prompt", app_name, project_path, config)

    def review_and_strip_code(self, changes_text: str, commits_text: str = "") -> str:
        """
        Review判断changes_text超出取前REVIEW_MAX_TOKENS个token，超出则截断changes_text，
        调用review_code方法，返回review_result，如果review_result是markdown格式，则去掉头尾的```
        :param changes_text:
        :param commits_text:
        :return:
        """
        # 从config中读取REVIEW_MAX_TOKENS（已包含默认值）
        review_max_tokens = int(self.config.get("REVIEW_MAX_TOKENS", "10000"))
        # 如果changes为空,打印日志
        if not changes_text:
            logger.info("代码为空, diffs_text = %", str(changes_text))
            return "代码为空"

        # 计算tokens数量，如果超过REVIEW_MAX_TOKENS，截断changes_text
        tokens_count = count_tokens(changes_text)
        if tokens_count > review_max_tokens:
            changes_text = truncate_text_by_tokens(changes_text, review_max_tokens)

        review_result = self.review_code(changes_text, commits_text).strip()
        if review_result.startswith("```markdown") and review_result.endswith("```"):
            return review_result[11:-3].strip()
        return review_result

    def review_code(self, diffs_text: str, commits_text: str = "") -> str:
        """Review 代码并返回结果"""
        messages = [
            self.prompts["system_message"],
            {
                "role": "user",
                "content": self.prompts["user_message"]["content"].format(
                    diffs_text=diffs_text, commits_text=commits_text
                ),
            },
        ]
        return self.call_llm(messages)

    @staticmethod
    def parse_review_score(review_text: str) -> int:
        """解析 AI 返回的 Review 结果，返回评分"""
        if not review_text:
            return 0
        match = re.search(r"总分[:：]\s*(\d+)分?", review_text)
        return int(match.group(1)) if match else 0


class LineReviewer(BaseReviewer):
    """行级代码审查器 - 生成结构化的行级评论"""

    def __init__(self, app_name: Optional[str] = None, project_path: Optional[str] = None, config: Optional[Dict[str, str]] = None):
        super().__init__("line_review_prompt", app_name, project_path, config)

    def review_code(self, diffs_text: str, commits_text: str = "") -> str:
        """Review 代码并返回 JSON 格式结果"""
        messages = [
            self.prompts["system_message"],
            {
                "role": "user",
                "content": self.prompts["user_message"]["content"].format(
                    diffs_text=diffs_text, commits_text=commits_text
                ),
            },
        ]
        return self.call_llm(messages)

    def review_and_parse(self, changes_text: str, commits_text: str = "") -> Dict[str, Any]:
        """
        执行行级审查并解析结果为结构化数据
        
        :param changes_text: 代码变更内容
        :param commits_text: 提交信息
        :return: 包含 summary, score, line_comments 的字典
        """
        # 从config中读取REVIEW_MAX_TOKENS（已包含默认值）
        review_max_tokens = int(self.config.get("REVIEW_MAX_TOKENS", "10000"))
        
        if not changes_text:
            logger.info("代码为空, 跳过行级审查")
            return {
                "summary": "代码为空",
                "score": 0,
                "line_comments": []
            }

        # 计算tokens数量，如果超过REVIEW_MAX_TOKENS，截断changes_text
        tokens_count = count_tokens(changes_text)
        if tokens_count > review_max_tokens:
            changes_text = truncate_text_by_tokens(changes_text, review_max_tokens)

        review_result = self.review_code(changes_text, commits_text).strip()
        
        # 解析 JSON 结果
        return self._parse_json_result(review_result)

    def _parse_json_result(self, result: str) -> Dict[str, Any]:
        """
        解析 LLM 返回的 JSON 结果
        
        :param result: LLM 返回的原始字符串
        :return: 解析后的字典
        """
        default_result = {
            "summary": "解析失败",
            "score": 0,
            "line_comments": []
        }
        
        if not result:
            return default_result
        
        # 尝试从 markdown 代码块中提取 JSON
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', result, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # 尝试直接解析
            json_str = result.strip()
        
        try:
            parsed = json.loads(json_str)
            
            # 验证必要字段
            if not isinstance(parsed, dict):
                logger.error(f"解析结果不是字典类型: {type(parsed)}")
                return default_result
            
            # 确保有必要的字段
            return {
                "summary": parsed.get("summary", ""),
                "score": parsed.get("score", 0),
                "line_comments": parsed.get("line_comments", [])
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}, 原始内容: {result[:500]}")
            return default_result

    def get_formatted_summary(self, review_result: Dict[str, Any]) -> str:
        """
        将行级审查结果格式化为 Markdown 摘要
        
        :param review_result: review_and_parse 的返回结果
        :return: Markdown 格式的摘要
        """
        summary = review_result.get("summary", "")
        score = review_result.get("score", 0)
        line_comments = review_result.get("line_comments", [])
        
        # 统计各严重程度的数量
        severity_counts = {"critical": 0, "warning": 0, "suggestion": 0, "info": 0}
        for comment in line_comments:
            severity = comment.get("severity", "info")
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        # 构建 Markdown 摘要
        md_lines = [
            "## 🔍 AI 代码审查报告",
            "",
            f"**总体评价**: {summary}",
            "",
            f"**评分**: {score}/100",
            "",
            "### 📊 问题统计",
            "",
            f"| 严重程度 | 数量 |",
            f"|---------|------|",
            f"| 🚨 严重问题 | {severity_counts['critical']} |",
            f"| ⚠️ 警告 | {severity_counts['warning']} |",
            f"| 💡 建议 | {severity_counts['suggestion']} |",
            f"| ℹ️ 提示 | {severity_counts['info']} |",
            "",
        ]
        
        if line_comments:
            md_lines.append("---")
            md_lines.append("")
            md_lines.append("*详细评论已添加到对应代码行*")
        
        return "\n".join(md_lines)

