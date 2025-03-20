import os

from dotenv import load_dotenv

from core.llm.client.base import BaseClient
from core.llm.client.deepseek import DeepSeekClient
from core.llm.client.ollama_client import OllamaClient
from core.llm.client.openai import OpenAIClient
from core.llm.client.zhipuai import ZhipuAIClient
from biz.utils.i18n import get_translator
_ = get_translator()

class Factory:
    @staticmethod
    def getClient(provider: str = None) -> BaseClient:
        load_dotenv()
        provider = provider or os.getenv("LLM_PROVIDER", "openai")
        chat_model_providers = {
            'zhipuai': lambda: ZhipuAIClient(),
            'openai': lambda: OpenAIClient(),
            'deepseek': lambda: DeepSeekClient(),
            'ollama': lambda : OllamaClient()
        }

        provider_func = chat_model_providers.get(provider)
        if provider_func:
            return provider_func()
        else:
            raise Exception(_('Unknown chat model provider: {provider}'))
