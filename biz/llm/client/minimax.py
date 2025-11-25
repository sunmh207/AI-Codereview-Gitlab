import os
from typing import Dict, List, Optional

from openai import OpenAI

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.log import logger


class MinimaxClient(BaseClient):
    # 支持的模型列表
    SUPPORTED_MODELS = {
        "MiniMax-M2",
        "MiniMax-M2-Stable"
    }

    # API 端点配置
    API_ENDPOINTS = {
        "china": {
            "openai": "https://api.minimaxi.com/v1",
            "anthropic": "https://api.minimaxi.com/anthropic"
        },
        "international": {
            "openai": "https://api.minimax.io/v1",
            "anthropic": "https://api.minimax.io/anthropic"
        }
    }

    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict[str, str]] = None):
        super().__init__(config)

        # API 格式配置：openai 或 anthropic
        self.api_format = self.get_config("MINIMAX_API_FORMAT", "openai")

        # 区域配置：china 或 international
        self.region = self.get_config("MINIMAX_REGION", "china").lower()

        # 根据格式和区域设置端点
        if self.region not in self.API_ENDPOINTS:
            raise ValueError(f"Unsupported region: {self.region}. Supported regions: {list(self.API_ENDPOINTS.keys())}")

        endpoints = self.API_ENDPOINTS[self.region]
        if self.api_format == "anthropic":
            # 支持新的配置键和向后兼容的旧键
            self.base_url = (self.get_config("MINIMAX_ANTHROPIC_BASE_URL") or
                           self.get_config("MINIMAX_API_BASE_URL") or
                           endpoints["anthropic"])
            self.default_model = (self.get_config("MINIMAX_ANTHROPIC_MODEL") or
                                self.get_config("MINIMAX_API_MODEL") or
                                "MiniMax-M2")
            # Anthropic API 需要特定的 key 配置
            self.api_key = (api_key or
                           self.get_config("MINIMAX_ANTHROPIC_API_KEY") or
                           self.get_config("MINIMAX_API_KEY"))
        else:
            # 支持新的配置键和向后兼容的旧键
            self.base_url = (self.get_config("MINIMAX_OPENAI_BASE_URL") or
                           self.get_config("MINIMAX_API_BASE_URL") or
                           endpoints["openai"])
            self.default_model = (self.get_config("MINIMAX_OPENAI_MODEL") or
                                self.get_config("MINIMAX_API_MODEL") or
                                "MiniMax-M2")
            self.api_key = api_key or self.get_config("MINIMAX_API_KEY")

        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set MINIMAX_API_KEY in the environment variables.")

        # 验证模型名称
        if self.default_model not in self.SUPPORTED_MODELS:
            logger.warning(f"Unknown model: {self.default_model}. Supported models: {self.SUPPORTED_MODELS}")

        # Minimax 使用标准的 OpenAI 兼容客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def _convert_messages_to_anthropic_format(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        将标准消息格式转换为 Anthropic API 格式
        Anthropic 要求消息列表以 user 角色开头，并可能需要不同的格式
        """
        anthropic_messages = []
        system_content = []

        # 先收集所有的 system 消息内容
        for msg in messages:
            if msg["role"] == "system":
                system_content.append(msg["content"])

        # 再处理非 system 消息
        for msg in messages:
            if msg["role"] != "system":
                anthropic_messages.append(msg)

        # 如果有 system 内容，将其合并到第一条 user 消息中
        if system_content:
            system_text = "\n\n".join(system_content)

            if anthropic_messages and anthropic_messages[0]["role"] == "user":
                # 将 system 内容添加到现有 user 消息前面
                anthropic_messages[0]["content"] = f"{system_text}\n\n{anthropic_messages[0]['content']}"
            else:
                # 如果没有 user 消息，创建一个包含 system 内容的 user 消息
                anthropic_messages.insert(0, {
                    "role": "user",
                    "content": system_text
                })

        # 确保第一条消息是 user 角色
        if anthropic_messages and anthropic_messages[0]["role"] != "user":
            anthropic_messages.insert(0, {
                "role": "user",
                "content": "Please respond to the following conversation."
            })

        return anthropic_messages

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    temperature: Optional[float] | NotGiven = NOT_GIVEN,
                    max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
                    ) -> str:
        """
        调用 Minimax API 进行对话补全
        支持两种格式：openai（默认）和 anthropic

        Args:
            messages: 对话消息列表，格式为 [{"role": "user", "content": "..."}]
            model: 可选的模型名称
            temperature: 温度参数，范围 (0.0, 1.0]
            max_tokens: 最大生成 token 数

        Returns:
            str: 模型的回复内容
        """
        model = model or self.default_model

        # 验证模型名称
        if model not in self.SUPPORTED_MODELS:
            logger.warning(f"Using unknown model: {model}. Supported models: {self.SUPPORTED_MODELS}")

        # 验证温度参数
        if temperature is not NOT_GIVEN:
            if isinstance(temperature, (int, float)):
                if not (0.0 < temperature <= 1.0):
                    logger.warning(f"Temperature {temperature} out of range (0.0, 1.0], using default 0.7")
                    temperature = 0.7
            else:
                temperature = 0.7
        else:
            temperature = 0.7

        # 验证 max_tokens 参数
        if max_tokens is not NOT_GIVEN:
            if isinstance(max_tokens, int) and max_tokens <= 0:
                logger.warning(f"max_tokens {max_tokens} must be positive, using default 4000")
                max_tokens = 4000
        else:
            max_tokens = 4000

        try:
            logger.debug(f"Sending request to MiniMax API ({self.region}, {self.api_format}). Model: {model}, Temperature: {temperature}")

            if self.api_format == "anthropic":
                # Anthropic 格式需要转换消息
                processed_messages = self._convert_messages_to_anthropic_format(messages)
                # Anthropic API 需要 max_tokens 参数
                completion = self.client.chat.completions.create(
                    model=model,
                    messages=processed_messages,  # type: ignore
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            else:
                # OpenAI 兼容格式
                processed_messages = messages
                completion = self.client.chat.completions.create(
                    model=model,
                    messages=processed_messages,  # type: ignore
                    temperature=temperature,
                    max_tokens=max_tokens
                )

            if not completion or not completion.choices:
                logger.error("Empty response from MiniMax API")
                return "AI服务返回为空，请稍后重试"

            content = completion.choices[0].message.content or ""
            logger.debug(f"MiniMax API response received, content length: {len(content)}")
            return content

        except Exception as e:
            error_msg = str(e)
            logger.error(f"MiniMax API ({self.api_format}, {self.region}) 调用失败: {error_msg}")

            # 根据错误类型返回友好的错误信息
            if "401" in error_msg:
                return f"MiniMax API认证失败，请检查API密钥是否正确（{self.region}区域）"
            elif "403" in error_msg:
                return f"MiniMax API访问被拒绝，请检查权限配置（{self.region}区域）"
            elif "404" in error_msg:
                return f"MiniMax API接口未找到，请检查API地址是否正确（{self.region}区域）"
            elif "429" in error_msg:
                return "MiniMax API请求频率过高，请稍后重试"
            elif "500" in error_msg:
                return f"MiniMax API服务器内部错误，请稍后重试（{self.region}区域）"
            elif "timeout" in error_msg.lower():
                return f"MiniMax API请求超时，请稍后重试（{self.region}区域）"
            else:
                return f"调用MiniMax API时出错: {error_msg}"