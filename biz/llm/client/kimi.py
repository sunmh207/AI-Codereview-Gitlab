
import os
from typing import Dict, List, Optional

from openai import OpenAI

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.log import logger


class KimiClient(BaseClient):
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self.api_key = api_key or self.get_config("KIMI_API_KEY")
        self.base_url = self.get_config("KIMI_API_BASE_URL", "https://api.moonshot.cn/v1")
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.default_model = self.get_config("KIMI_API_MODEL", "kimi-k2-turbo-preview")

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        try:
            model = model or self.default_model
            if not model:
                model = "kimi-k2-turbo-preview"
            logger.debug(f"Sending request to Kimi API. Model: {model}, Messages: {messages}")
            
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages  # type: ignore
            )
            
            if not completion or not completion.choices:
                logger.error("Empty response from Kimi API")
                return "AI服务返回为空，请稍后重试"
                
            return completion.choices[0].message.content or ""
            
        except Exception as e:
            logger.error(f"Kimi API error: {str(e)}")
            # 检查是否是认证错误
            if "401" in str(e):
                return "Kimi API认证失败，请检查API密钥是否正确"
            elif "404" in str(e):
                return "Kimi API接口未找到，请检查API地址是否正确"
            else:
                return f"调用Kimi API时出错: {str(e)}"
