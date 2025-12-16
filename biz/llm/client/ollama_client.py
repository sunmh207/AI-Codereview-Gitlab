import os
import re
from typing import Dict, List, Optional

from ollama import ChatResponse
from ollama import Client

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN


class OllamaClient(BaseClient):
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self.default_model = self.get_config("OLLAMA_API_MODEL", "deepseek-r1-8k:14b")
        self.base_url = self.get_config("OLLAMA_API_BASE_URL", "http://127.0.0.1:11434")
        self.client = Client(
            host=self.base_url,
        )

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
        model = model or self.default_model or "deepseek-r1-8k:14b"
        response: ChatResponse = self.client.chat(model, messages)  # type: ignore
        content = response['message']['content']
        return self._extract_content(content)
