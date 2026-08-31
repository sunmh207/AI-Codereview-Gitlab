import json
import os
from typing import Dict, List, Optional

from openai import OpenAI, AuthenticationError, NotFoundError

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.log import logger


class OrcaRouterClient(BaseClient):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ORCAROUTER_API_KEY")
        self.base_url = os.getenv("ORCAROUTER_API_BASE_URL", "https://api.orcarouter.ai/v1")
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")

        # OrcaRouter exposes an OpenAI-compatible endpoint, so the OpenAI SDK works as-is.
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.default_model = os.getenv("ORCAROUTER_API_MODEL", "deepseek/deepseek-chat")

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        try:
            model = model or self.default_model
            logger.debug(f"Sending request to OrcaRouter API. Model: {model}, Messages: {messages}")

            completion = self.client.chat.completions.create(
                model=model,
                messages=messages
            )

            if not completion or not completion.choices:
                logger.error("Empty response from OrcaRouter API")
                return "AI service returned an empty response, please try again later"

            return completion.choices[0].message.content

        except AuthenticationError:
            logger.error("OrcaRouter API authentication failed")
            return "OrcaRouter API authentication failed, please check your API key"
        except NotFoundError as e:
            logger.error(f"OrcaRouter API endpoint or model not found: {str(e)}")
            return "OrcaRouter API endpoint or model not found, please check your API base URL and model"
        except Exception as e:
            logger.error(f"OrcaRouter API error: {str(e)}")
            return f"OrcaRouter API error: {str(e)}"

    def chat_with_tools(self,
                        messages: List[Dict],
                        tools: Optional[List[Dict]] = None,
                        model: Optional[str] | NotGiven = NOT_GIVEN,
                        ) -> Dict:
        model = model or self.default_model
        kwargs = {"model": model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        completion = self.client.chat.completions.create(**kwargs)
        msg = completion.choices[0].message
        tool_calls: List[Dict] = []
        for tc in (msg.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({"id": tc.id, "name": tc.function.name, "arguments": args})
        return {
            "content": msg.content,
            "tool_calls": tool_calls,
            "raw": completion,
        }
