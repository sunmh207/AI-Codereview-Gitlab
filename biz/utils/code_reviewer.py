import os
import re
import yaml
import abc
from typing import Dict, Any, List

from biz.utils.log import logger
from biz.llm.factory import Factory
from biz.utils.i18n import get_translator
from biz.utils.token_util import count_tokens, truncate_text_by_tokens

_ = get_translator()


class BaseReviewer(abc.ABC):
    """代码审查基类"""

    def __init__(self, prompt_key: str):
        self.client = Factory().getClient()
        self.prompts = self._load_prompts(prompt_key)

    def _load_prompts(self, prompt_key: str) -> Dict[str, Any]:
        """加载提示词配置"""
        lang = os.environ.get('LANGUAGE', 'zh_CN')
        prompt_templates_file = os.path.join("locales", lang, "prompt_templates.yml")
        try:
            with open(prompt_templates_file, "r") as file:
                prompts = yaml.safe_load(file).get(prompt_key, {})
                system_prompt = prompts.get("system_prompt")
                user_prompt = prompts.get("user_prompt")

                if not system_prompt or not user_prompt:
                    raise ValueError(_("提示词配置 `{prompt_key}` 为空或格式不正确").format(prompt_key=prompt_key))

                return {
                    "system_message": {"role": "system", "content": system_prompt},
                    "user_message": {"role": "user", "content": user_prompt},
                }
        except (FileNotFoundError, KeyError, yaml.YAMLError) as e:
            logger.error(_("加载提示词配置失败: {e}").format(e=e))
            raise Exception(_("提示词配置加载失败: {e}").format(e=e))

    def call_llm(self, messages: List[Dict[str, Any]]) -> str:
        """调用 LLM 进行代码审核"""
        logger.info(_("向 AI 发送代码 Review 请求, messages: {messages}").format(messages=messages))
        review_result = self.client.completions(messages=messages)
        logger.info(_("收到 AI 返回结果: {review_result}").format(review_result=review_result))
        return review_result

    @abc.abstractmethod
    def review_code(self, *args, **kwargs) -> str:
        """抽象方法，子类必须实现"""
        pass


class CodeReviewer(BaseReviewer):
    """代码 Diff 级别的审查"""

    def __init__(self):
        super().__init__("code_review_prompt")

    def review_and_strip_code(self, changes_text: str, commits_text: str = '') -> str:
        # 如果超长，取前REVIEW_MAX_TOKENS个token
        review_max_tokens = int(os.getenv('REVIEW_MAX_TOKENS', 10000))
        # 如果changes为空,打印日志
        if not changes_text:
            logger.info(_('代码为空, diffs_text = {}').format(str(changes_text)))
            return _('代码为空')

        # 计算tokens数量，如果超过REVIEW_MAX_TOKENS，截断changes_text
        tokens_count = count_tokens(changes_text)
        if tokens_count > review_max_tokens:
            changes_text = truncate_text_by_tokens(changes_text, review_max_tokens)

        review_result = CodeReviewer().review_code(changes_text, commits_text).strip()
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
                    diffs_text=diffs_text,
                    commits_text=commits_text
                ),
            },
        ]
        return self.call_llm(messages)

    @staticmethod
    def parse_review_score(review_text: str) -> int:
        """解析 AI 返回的 Review 结果，返回评分"""
        if not review_text:
            return 0
        match = re.search(_("总分[:：]\\s*\\**(\\d+)分?"), review_text)
        return int(match.group(1)) if match else 0


class CodeBaseReviewer(BaseReviewer):
    """代码库级别的审查"""

    def __init__(self):
        super().__init__("codebase_review_prompt")

    def review_code(self, language: str, directory_structure: str) -> str:
        """Review 代码库并返回结果"""
        messages = [
            self.prompts["system_message"],
            {
                "role": "user",
                "content": self.prompts["user_message"]["content"].format(
                    language=language,
                    directory_structure=directory_structure,
                ),
            },
        ]
        return self.call_llm(messages)
