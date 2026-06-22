import re
from abc import abstractmethod
from typing import List, Dict, Optional

from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.log import logger


class BaseClient:
    """ Base class for chat models client. """

    def ping(self) -> bool:
        """Ping the model to check connectivity."""
        try:
            result = self.completions(messages=[{"role": "user", "content": '请仅返回 "ok"。'}])
            cleaned = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL)
            return cleaned.strip() == "ok"
        except Exception:
            logger.error("尝试连接LLM失败， {e}")
            return False

    @abstractmethod
    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        """Chat with the model.
        """

    def chat_with_tools(self,
                        messages: List[Dict],
                        tools: Optional[List[Dict]] = None,
                        model: Optional[str] | NotGiven = NOT_GIVEN,
                        ) -> Dict:
        """Chat with native tool-use support.

        Default implementation raises NotImplementedError. Providers that
        support native tool calling should override this method.

        Args:
            messages: OpenAI-style message list.
            tools:    OpenAI-style tool schema list (each item has
                      {"type": "function", "function": {...}}).
            model:    Optional model override.

        Returns:
            A dict with keys:
              - "content": Optional[str]   — assistant text (may be None)
              - "tool_calls": List[Dict]   — each {"id", "name", "arguments": dict}
              - "raw": Any                 — provider-specific response
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not implement native tool-use; "
            "use LLMAdapter's JSON-protocol fallback instead."
        )
