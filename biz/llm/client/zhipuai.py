import os
from typing import Dict, List, Optional

from zhipuai import ZhipuAI

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN


class ZhipuAIClient(BaseClient):
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self.api_key = api_key or self.get_config("ZHIPUAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")

        self.client = ZhipuAI(api_key=self.api_key)
        self.default_model = self.get_config("ZHIPUAI_API_MODEL", "GLM-4-Flash")

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        model = model or self.default_model or "GLM-4-Flash"
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
        )
        return completion.choices[0].message.content or ""  # type: ignore
