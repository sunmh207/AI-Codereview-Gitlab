import os
from typing import Dict, List, Optional

from openai import OpenAI

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN


class OpenAIClient(BaseClient):
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self.api_key = api_key or self.get_config("OPENAI_API_KEY")
        self.base_url = self.get_config("OPENAI_API_BASE_URL", "https://api.openai.com")
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.default_model = self.get_config("OPENAI_API_MODEL", "gpt-4o-mini")

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        model = model or self.default_model or "gpt-4o-mini"
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
        )
        return completion.choices[0].message.content or ""
