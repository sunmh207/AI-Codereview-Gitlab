import os
from typing import Dict, Optional

from biz.llm.client.base import BaseClient
from biz.llm.client.deepseek import DeepSeekClient
from biz.llm.client.kimi import KimiClient
from biz.llm.client.minimax import MinimaxClient
from biz.llm.client.ollama_client import OllamaClient
from biz.llm.client.openai import OpenAIClient
from biz.llm.client.qwen import QwenClient
from biz.llm.client.zhipuai import ZhipuAIClient
from biz.utils.log import logger


class Factory:
    @staticmethod
    def getClient(provider: Optional[str] = None, config: Optional[Dict[str, str]] = None) -> BaseClient:
        """
        获取LLM客户端
        :param provider: 提供商名称
        :param config: 项目专属配置字典，优先级高于全局环境变量
        :return: LLM客户端实例
        """
        config = config or {}
        # 优先从 config 读取，其次从 provider 参数，最后从环境变量读取
        provider = provider or config.get("LLM_PROVIDER") or os.environ.get("LLM_PROVIDER", "openai")
        chat_model_providers = {
            'zhipuai': lambda: ZhipuAIClient(config=config),
            'openai': lambda: OpenAIClient(config=config),
            'deepseek': lambda: DeepSeekClient(config=config),
            'qwen': lambda: QwenClient(config=config),
            'ollama': lambda : OllamaClient(config=config),
            'kimi': lambda: KimiClient(config=config),
            'minimax': lambda: MinimaxClient(config=config)
        }

        provider_func = chat_model_providers.get(provider)
        if provider_func:
            return provider_func()
        else:
            raise Exception(f'Unknown chat model provider: {provider}')
