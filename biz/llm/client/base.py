from abc import abstractmethod
from typing import List, Dict, Optional

from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.log import logger


class BaseClient:
    """ Base class for chat models client. """
    
    def __init__(self, config: Optional[Dict[str, str]] = None):
        """
        初始化LLM客户端
        :param config: 项目专属配置字典，优先级高于全局环境变量
        """
        self.config = config or {}
    
    def get_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取配置项，优先从config字典读取，若不存在则从环境变量读取
        :param key: 配置键
        :param default: 默认值
        :return: 配置值
        """
        import os
        # 优先从config字典读取，其次从环境变量读取，最后使用默认值
        return self.config.get(key) or os.getenv(key, default)

    def ping(self) -> bool:
        """Ping the model to check connectivity."""
        try:
            result = self.completions(messages=[{"role": "user", "content": '请仅返回 "ok"。'}])
            return bool(result and result.strip() == "ok")
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
