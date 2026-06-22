import abc
import os
import re
from typing import Dict, Any, List

import yaml
from jinja2 import Template

from biz.llm.factory import Factory
from biz.utils.log import logger
from biz.utils.token_util import count_tokens, truncate_text_by_tokens


class BaseReviewer(abc.ABC):
    """代码审查基类"""

    def __init__(self, prompt_key: str):
        self.client = Factory().getClient()
        self.prompts = self._load_prompts(prompt_key, os.getenv("REVIEW_STYLE", "professional"))

    def _load_prompts(self, prompt_key: str, style="professional") -> Dict[str, Any]:
        """加载提示词配置"""
        prompt_templates_file = "conf/prompt_templates.yml"
        try:
            # 在打开 YAML 文件时显式指定编码为 UTF-8，避免使用系统默认的 GBK 编码。
            with open(prompt_templates_file, "r", encoding="utf-8") as file:
                prompts = yaml.safe_load(file).get(prompt_key, {})

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

    def __init__(self):
        super().__init__("code_review_prompt")

    def review_and_strip_code(self, changes_text: str, commits_text: str = "") -> str:
        """
        Review判断changes_text超出取前REVIEW_MAX_TOKENS个token，超出则截断changes_text，
        调用review_code方法，返回review_result，如果review_result是markdown格式，则去掉头尾的```
        :param changes_text:
        :param commits_text:
        :return:
        """
        # 如果超长，取前REVIEW_MAX_TOKENS个token
        review_max_tokens = int(os.getenv("REVIEW_MAX_TOKENS", 10000))
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

    @staticmethod
    def count_skill_findings(review_text: str) -> Dict[str, int]:
        """统计 skill 审查报告中各严重等级(P0-P3)的问题数量。

        依据 skill 输出格式: `### P0 - 严重` 等小节下, 形如 `1. **[file:line]** 标题`
        的编号条目即为一个问题。
        """
        counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        if not review_text:
            return counts
        headers = list(re.finditer(r"^###\s*(P[0-3])\b", review_text, re.MULTILINE))
        for i, m in enumerate(headers):
            sev = m.group(1)
            start = m.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(review_text)
            section = review_text[start:end]
            # 仅统计 "数字. **" 开头的条目，避免误计描述中的编号子项
            counts[sev] += len(re.findall(r"^\s*\d+\.\s+\*\*", section, re.MULTILINE))
        return counts

    @staticmethod
    def score_skill_review(review_text: str) -> int:
        """按问题权重对 skill 审查报告扣分: 基础 100 分, 各等级扣分权重可由环境变量覆盖。"""
        deduct = {
            "P0": int(os.getenv("REVIEW_SCORE_DEDUCT_P0", 40)),
            "P1": int(os.getenv("REVIEW_SCORE_DEDUCT_P1", 20)),
            "P2": int(os.getenv("REVIEW_SCORE_DEDUCT_P2", 10)),
            "P3": int(os.getenv("REVIEW_SCORE_DEDUCT_P3", 2)),
        }
        counts = CodeReviewer.count_skill_findings(review_text)
        score = 100 - sum(deduct[sev] * n for sev, n in counts.items())
        return max(0, score)

    @staticmethod
    def compute_score(review_text: str) -> int:
        """统一评分入口: 含"总分"的 LLM diff 报告按原正则解析;
        否则视为 skill 的 P0-P3 报告, 按问题权重扣分。
        """
        if review_text and re.search(r"总分[:：]", review_text):
            return CodeReviewer.parse_review_score(review_text)
        return CodeReviewer.score_skill_review(review_text)

