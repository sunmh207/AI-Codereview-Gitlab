import abc
import json
import os
import re
from typing import Dict, Any, List

import yaml
from jinja2 import Template

from biz.llm.factory import Factory
from biz.utils.code_parser import parse_single_file_diff
from biz.utils.log import logger
from biz.utils.token_util import count_tokens, truncate_text_by_tokens


class BaseReviewer(abc.ABC):
    """代码审查基类"""

    def __init__(self):
        self.client = Factory().getClient()
        self.prompts = self._load_prompts(os.getenv("REVIEW_STYLE", "professional"))

    def _load_prompts(self, style="professional") -> Dict[str, Any]:
        """加载提示词配置"""
        prompt_templates_file = "conf/prompt_templates.yml"
        try:
            # 在打开 YAML 文件时显式指定编码为 UTF-8，避免使用系统默认的 GBK 编码。
            with open(prompt_templates_file, "r", encoding="utf-8") as file:
                prompts = yaml.safe_load(file)

                # 使用Jinja2渲染模板
                def render_template(template_str: str) -> str:
                    return Template(template_str).render(style=style)
                for k, v in prompts.items():
                    system_prompt = render_template(v["system_prompt"])
                    user_prompt = render_template(v["user_prompt"])
                    prompts[k] = {
                        "system_message": {"role": "system", "content": system_prompt},
                        "user_message": {"role": "user", "content": user_prompt},
                    }
                return prompts
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
        super().__init__()

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
            self.prompts['code_review_prompt']["system_message"],
            {
                "role": "user",
                "content": self.prompts['code_review_prompt']["user_message"]["content"].format(
                    diffs_text=diffs_text, commits_text=commits_text
                ),
            },
        ]
        return self.call_llm(messages)

    def detail_review(self, changes: list) -> List[Dict]:
        all_reviews: List[Dict] = []
        # 对每个变更的文件进行详细review
        for change in changes:
            file_diff_text = change.get('diff')
            new_path = change.get('new_path')
            old_path = change.get('old_path')
            is_renamed = change.get('renamed_file', False)
            logger.info(f"解析文件 diff: {new_path} (旧路径: {old_path if is_renamed else 'N/A'})")
            try:
                file_parsed_changes = parse_single_file_diff(file_diff_text, new_path, old_path if is_renamed else None)
                if not file_parsed_changes or not file_parsed_changes.get("changes"):
                    logger.info(f"未从 {new_path} 的 diff 中解析出变更。")
                    continue

                logger.info(f"成功解析 {new_path} 的 {len(file_parsed_changes['changes'])} 处变更。")
                input_data = {
                    "file_meta": {
                        "path": file_parsed_changes["path"],
                        "old_path": file_parsed_changes.get("old_path"),
                        "lines_changed": file_parsed_changes.get("lines_changed", len(file_parsed_changes["changes"])),
                        "context": file_parsed_changes["context"]
                    },
                    "changes": file_parsed_changes["changes"]
                }
                input_json_string = json.dumps(input_data, indent=2, ensure_ascii=False)
                json_content = f"```json\n{input_json_string}\n```"

                messages = [
                    self.prompts['detail_review_prompt']["system_message"],
                    {
                        "role": "user",
                        "content": self.prompts['detail_review_prompt']["user_message"]["content"].
                        format(json_content=json_content),
                    },
                ]

                review_json_str = self.call_llm(messages)
                parsed_output = json.loads(review_json_str)
                reviews_for_file = []
                if isinstance(parsed_output, list):
                    reviews_for_file = parsed_output
                elif isinstance(parsed_output, dict):  # Check if the dict contains a list
                    found_list = False
                    for key, value in parsed_output.items():
                        if isinstance(value, list):
                            reviews_for_file = value
                            found_list = True
                            logger.info(f"在 LLM 输出的键 '{key}' 下找到审查列表。")
                            break
                    if not found_list:
                        logger.warning(
                            f"文件 {new_path} 的 LLM 输出是一个字典，但未找到列表值。输出: {review_json_str}")
                        # Attempt to use the dict as a single review item if it matches structure,
                        # otherwise, it will be filtered out by validation below.
                        reviews_for_file = [parsed_output]
                else:
                    logger.warning(
                        f"文件 {new_path} 的 LLM 输出不是 JSON 列表或预期的字典。输出: {review_json_str}")

                valid_reviews_for_file = []
                for review in reviews_for_file:
                    if isinstance(review, dict) and all(
                            k in review for k in
                            ["file", "lines", "category", "severity", "analysis", "suggestion"]):
                        if review.get("file") != new_path:
                            logger.warning(
                                f"修正审查中的文件路径从 '{review.get('file')}' 为 '{new_path}'")
                            review["file"] = new_path
                        valid_reviews_for_file.append(review)
                    else:
                        logger.warning(f"跳过文件 {new_path} 的无效审查项结构: {review}")
                all_reviews.extend(valid_reviews_for_file)
            except Exception as e:
                logger.warning(f"文件 {new_path} 的代码审查出错: {e}")
        return all_reviews

    @staticmethod
    def parse_review_score(review_text: str) -> int:
        """解析 AI 返回的 Review 结果，返回评分"""
        if not review_text:
            return 0
        match = re.search(r"总分[:：]\s*(\d+)分?", review_text)
        return int(match.group(1)) if match else 0

