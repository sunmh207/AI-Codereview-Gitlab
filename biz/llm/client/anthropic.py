import os
from typing import Dict, List, Optional

import httpx
from anthropic import Anthropic

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN


class AnthropicClient(BaseClient):
    @staticmethod
    def _real(value: str):
        """过滤 .env.dist 占位值(xxxx)与空值，返回真实值或 None。"""
        if value and value.strip().lower() not in ("", "xxxx", "xxx"):
            return value
        return None

    def __init__(self, api_key: str = None):
        # 认证: 支持两种方式
        #   - ANTHROPIC_API_KEY  -> x-api-key 头(官方 API)
        #   - ANTHROPIC_AUTH_TOKEN -> Authorization: Bearer 头(anyrouter 等中转网关)
        self.api_key = self._real(api_key) or self._real(os.getenv("ANTHROPIC_API_KEY"))
        self.auth_token = self._real(os.getenv("ANTHROPIC_AUTH_TOKEN"))
        # 自定义 URL: 同时认 SDK 风格(ANTHROPIC_API_BASE_URL)与 CLI 风格(ANTHROPIC_BASE_URL)
        self.base_url = self._real(os.getenv("ANTHROPIC_API_BASE_URL")) or self._real(os.getenv("ANTHROPIC_BASE_URL"))

        if not self.api_key and not self.auth_token:
            raise ValueError(
                "需要认证信息: 请设置 ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN(中转网关)。"
            )

        # Create a custom httpx client to avoid proxy-related issues
        # This prevents the 'proxies' parameter error when environment proxy variables are set
        http_client = httpx.Client()

        kwargs = {"http_client": http_client}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        # auth_token 优先(Bearer)，否则用 api_key(x-api-key)
        if self.auth_token:
            kwargs["auth_token"] = self.auth_token
        else:
            kwargs["api_key"] = self.api_key

        # beta 特性(如 1M 上下文 context-1m-2025-08-07)：与 claude CLI 同名变量 ANTHROPIC_BETAS，
        # 逗号分隔，作为 anthropic-beta 头发送，使 SDK 与 CLI 两条路一致启用。
        betas = self._real(os.getenv("ANTHROPIC_BETAS"))
        if betas:
            kwargs["default_headers"] = {"anthropic-beta": betas}

        self.client = Anthropic(**kwargs)

        self.default_model = os.getenv("ANTHROPIC_API_MODEL", "claude-sonnet-4-20250514")

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        model = model or self.default_model

        # Convert messages to Anthropic format
        # Anthropic requires separating system messages from user/assistant messages
        system_message = None
        anthropic_messages = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if role == "system":
                # Anthropic uses a separate system parameter
                system_message = content
            else:
                # Keep user and assistant messages
                anthropic_messages.append({
                    "role": role,
                    "content": content
                })

        # Create completion with Anthropic API
        response = self.client.messages.create(
            model = model,
            system = system_message,
            messages = anthropic_messages,
            max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096")),
        )

        # Extract text from response
        return response.content[0].text
