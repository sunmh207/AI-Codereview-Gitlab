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
        self.prompts = self._load_prompts(
            prompt_key, os.getenv("REVIEW_STYLE", "professional")
        )

    def _load_prompts(self, prompt_key: str, style="professional") -> Dict[str, Any]:
        """加载提示词配置"""
        prompt_templates_file = "conf/prompt_templates.yml"
        try:
            # 在打开 YAML 文件时显式指定编码为 UTF-8，避免使用系统默认的 GBK 编码。
            with open(prompt_templates_file, "r", encoding="utf-8") as file:
                prompts = yaml.safe_load(file).get(prompt_key, {})

                # 使用Jinja2渲染system_prompt（只包含style变量）
                def render_template(template_str: str) -> str:
                    return Template(template_str).render(style=style)

                system_prompt = render_template(prompts["system_prompt"])
                # user_prompt需要保留模板，因为需要在review_code时传入动态变量，判断是否有参考文件内容
                user_prompt_template = prompts["user_prompt"]

                return {
                    "system_message": {"role": "system", "content": system_prompt},
                    "user_message_template": user_prompt_template,  # 保存模板而不是渲染后的内容
                    "style": style,  # 保存style用于后续渲染
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

    def review_and_strip_code(
        self, changes_text: str, commits_text: str = "", file_contents: dict = None
    ) -> str:
        """
        Review判断changes_text超出取前REVIEW_MAX_TOKENS个token，超出则截断changes_text，
        调用review_code方法，返回review_result，如果review_result是markdown格式，则去掉头尾的```
        :param changes_text: diff文本
        :param commits_text: 提交信息
        :param file_contents: 文件内容字典，key为文件路径，value为文件内容
        :return:
        """
        # 如果超长，取前REVIEW_MAX_TOKENS个token
        review_max_tokens = int(os.getenv("REVIEW_MAX_TOKENS", 10000))
        # 如果changes为空,打印日志
        if not changes_text:
            logger.info("代码为空, diffs_text = %", str(changes_text))
            return "代码为空"

        # 计算diff的tokens数量
        diff_tokens = count_tokens(changes_text)
        processed_file_contents = {}
        # 如果diff超过限制，先截断diff，然后不添加文件内容
        if diff_tokens > review_max_tokens:
            changes_text = truncate_text_by_tokens(changes_text, review_max_tokens)
            diff_tokens = review_max_tokens
            logger.info(
                f"Diff tokens exceed REVIEW_MAX_TOKENS ({review_max_tokens}), truncated diff and skipping file contents"
            )
        else:
            # diff未超过限制，尝试添加文件内容
            if file_contents:
                # 计算剩余可用tokens（为diff保留空间）
                available_tokens = review_max_tokens - diff_tokens

                if available_tokens > 0:
                    # 按顺序添加文件内容，直到空间用完
                    remaining_tokens = available_tokens
                    for file_path, content in file_contents.items():
                        file_tokens = count_tokens(content)
                        if file_tokens <= remaining_tokens:
                            # 文件内容可以完整添加
                            processed_file_contents[file_path] = content
                            remaining_tokens -= file_tokens
                        elif remaining_tokens > 0:
                            # 文件内容超过剩余空间，截断后添加
                            processed_file_contents[file_path] = (
                                truncate_text_by_tokens(content, remaining_tokens)
                            )
                            remaining_tokens = 0
                            break
                        else:
                            # 没有剩余空间，跳过后续文件
                            break
                else:
                    logger.debug(
                        f"No available tokens for file contents (diff_tokens: {diff_tokens}, max: {review_max_tokens})"
                    )

        review_result = self.review_code(
            changes_text, commits_text, processed_file_contents
        ).strip()
        if review_result.startswith("```markdown") and review_result.endswith("```"):
            return review_result[11:-3].strip()
        return review_result

    def review_code(
        self, diffs_text: str, commits_text: str = "", file_contents: dict = None
    ) -> str:
        """Review 代码并返回结果"""
        # 格式化文件内容
        file_contents_text = ""
        if file_contents:
            file_contents_list = []
            for file_path, content in file_contents.items():
                file_contents_list.append(
                    f"文件路径: {file_path}\n文件内容:\n```\n{content}\n```"
                )
            file_contents_text = "\n\n".join(file_contents_list)

        # 使用Jinja2渲染user_prompt模板
        user_prompt_template = self.prompts["user_message_template"]
        user_prompt_content = Template(user_prompt_template).render(
            style=self.prompts["style"],
            diffs_text=diffs_text,
            commits_text=commits_text,
            file_contents_text=file_contents_text,
        )

        messages = [
            self.prompts["system_message"],
            {
                "role": "user",
                "content": user_prompt_content,
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
