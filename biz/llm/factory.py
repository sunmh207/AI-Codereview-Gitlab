import os

from biz.llm.client.base import BaseClient
from biz.llm.client.deepseek import DeepSeekClient
from biz.llm.client.ollama_client import OllamaClient
from biz.llm.client.openai import OpenAIClient
from biz.llm.client.zhipuai import ZhipuAIClient
from biz.utils.i18n import get_translator
from biz.utils.log import logger

_ = get_translator()


class Factory:
    @staticmethod
    def getClient(provider: str = None) -> BaseClient:
        provider = provider or os.getenv("LLM_PROVIDER", "openai")
        chat_model_providers = {
            'zhipuai': lambda: ZhipuAIClient(),
            'openai': lambda: OpenAIClient(),
            'deepseek': lambda: DeepSeekClient(),
            'ollama': lambda: OllamaClient()
        }

        provider_func = chat_model_providers.get(provider)
        if provider_func:
            return provider_func()
        else:
            raise Exception(_('Unknown chat model provider: {provider}'.format(provider=provider)))
