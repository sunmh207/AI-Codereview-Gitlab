import os
import re

import yaml

from biz.utils.log import logger
from biz.llm.factory import Factory
from biz.utils.i18n import get_translator
_ = get_translator()


class CodeReviewer:
    def __init__(self):
        self.client = Factory().getClient()
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> dict:
        """加载提示词配置"""
        lang = os.environ.get('LANGUAGE', 'zh_CN')
        prompt_templates_file = os.path.join("locales", lang, "prompt_templates.yml")
        with open(prompt_templates_file, "r") as file:
            prompt_templates = yaml.safe_load(file)
            system_prompt = prompt_templates['system_prompt']
            user_prompt = prompt_templates['user_prompt']

        if not system_prompt or not user_prompt:
            logger.warning(_("未找到提示词配置{}").format(prompt_templates_file))
            # 抛出异常
            raise Exception(_("未找到提示词配置{}，或配置格式不正确").format(prompt_templates_file))

        return {
            "code_review": {
                "system_message": {
                    "role": "system",
                    "content": system_prompt
                },
                "user_message": {
                    "role": "user",
                    "content": user_prompt
                }
            }
        }

    def review_and_strip_code(self, changes_text: str, commits_text: str = '') -> str:
        # 如果超长，取前REVIEW_MAX_LENGTH字符
        review_max_length = int(os.getenv('REVIEW_MAX_LENGTH', 5000))
        # 如果changes为空,打印日志
        if not changes_text:
            logger.info(_('代码为空, diffs_text = {}').format(str(changes_text)))
            return _('代码为空')

        if len(changes_text) > review_max_length:
            changes_text = changes_text[:review_max_length]
            logger.info(_('文本超长，截段后content: {}').format(changes_text))
        review_result = self.review_code(changes_text, commits_text).strip()
        if review_result.startswith("```markdown") and review_result.endswith("```"):
            return review_result[11:-3].strip()
        return review_result

    def review_code(self, diffs_text: str, commits_text: str = "") -> str:
        """Review代码，并返回结果"""
        prompts = self.prompts["code_review"]
        messages = [
            prompts["system_message"],
            {
                "role": "user",
                "content": prompts["user_message"]["content"].format(
                    diffs_text=diffs_text,
                    commits_text=commits_text
                )
            }
        ]
        return self.call_llm(messages)

    def call_llm(self, messages: list) -> str:
        logger.info(_("向AI发送代码Review请求, message: {}").format(messages))
        review_result = self.client.completions(
            messages=messages
        )
        logger.info(_("收到AI返回结果: {}").format(review_result))
        return review_result

    @staticmethod
    def parse_review_score(review_text: str) -> int:
        """解析AI返回的Review结果，返回评分"""
        if not review_text:
            return 0  # 如果review_text为空，返回 0
        match = re.search(_("总分[:：]\\s*\\**(\\d+)分?"), review_text)

        if match:
            return int(match.group(1))  # 提取数值部分并转换为整数
        return 0  # 如果未匹配到，返回 0
