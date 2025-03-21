import os
from typing import Dict, List, Optional

from openai import OpenAI

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.i18n import get_translator
from biz.utils.log import logger

_ = get_translator()


class DeepSeekClient(BaseClient):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com")
        if not self.api_key:
            raise ValueError(_("API key is required. Please provide it or set it in the environment variables."))

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)  # DeepSeek supports OpenAI API SDK
        self.default_model = os.getenv("DEEPSEEK_API_MODEL", "deepseek-chat")

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        try:
            model = model or self.default_model
            logger.debug(_("Sending request to DeepSeek API. Model: {model}, Messages: {messages}").format(model=model,
                                                                                                           messages=messages))

            completion = self.client.chat.completions.create(
                model=model,
                messages=messages
            )

            if not completion or not completion.choices:
                logger.error(_("Empty response from DeepSeek API"))
                return _("AI服务返回为空，请稍后重试")

            return completion.choices[0].message.content

        except Exception as e:
            logger.error(_("DeepSeek API error: {e}").format(e=str(e)))
            # 检查是否是认证错误
            if "401" in str(e):
                return _("DeepSeek API认证失败，请检查API密钥是否正确")
            elif "404" in str(e):
                return _("DeepSeek API接口未找到，请检查API地址是否正确")
            else:
                return _("调用DeepSeek API时出错: {e}").format(e=str(e))
