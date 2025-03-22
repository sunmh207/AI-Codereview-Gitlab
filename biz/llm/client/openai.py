import os
from typing import Dict, List, Optional

from openai import OpenAI

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN


class OpenAIClient(BaseClient):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com")
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.default_model = os.getenv("OPENAI_API_MODEL", "gpt-4o-mini")

    def _extract_content(self, content: str) -> str:
        """
        从内容中提取<think>...</think>标签之外的部分。

        Args:
            content (str): 原始内容。

        Returns:
            str: 提取后的内容。
        """
        if "<think>" in content and "</think>" not in content:
            # 大模型回复的时候，思考链有可能截断，那么果断忽略回复，返回空
            return "COT ABORT!"
        elif "<think>" not in content and "</think>" in content:
            return content.split("</think>", 1)[1].strip()
        elif re.search(r'<think>.*?</think>', content, re.DOTALL):
            return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        return content
    
    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        model = model or self.default_model
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return self._extract_content(completion.choices[0].message.content)
