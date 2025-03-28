import abc
import os
from abc import abstractmethod
from typing import List, Dict, Any

from biz.llm.factory import Factory
from biz.utils.token_util import count_tokens, truncate_text_by_tokens


class BaseReviewFunc(abc.ABC):
    """
    Review功能的基础类，定义了一些通用的方法和属性。
    """

    def get_user_input(self, prompt: str, default=None, input_type=str):
        """
        获取用户输入，支持默认值和类型转换。

        Args:
            prompt (str): 提示信息。
            default: 默认值。
            input_type: 输入值的类型（如 int, str, bool 等）。

        Returns:
            用户输入的值或默认值。
        """
        user_input = input(f"{prompt} (默认: {default}): ").strip()
        if not user_input:
            return default
        try:
            return input_type(user_input)
        except ValueError:
            print(f"输入无效，请输入 {input_type.__name__} 类型的值。")
            return self.get_user_input(prompt, default, input_type)

    def confirm_action(self, prompt: str) -> bool:
        while True:
            user_input = input(prompt).strip().lower()
            if user_input in ["y", "yes"]:
                return True
            elif user_input in ["n", "no"]:
                return False
            else:
                print("请输入 'y' 或 'n' 确认。")

    @abstractmethod
    def process(self):
        """
        处理逻辑的入口方法，子类需要实现具体的处理逻辑。
        """
        raise NotImplementedError


class LLMReviewFunc(BaseReviewFunc):
    """
    基于LLM的Review功能的基础类，定义了一些通用的方法和属性。
    """
    DEFAULT_REVIEW_MAX_TOKENS = 10000

    def __init__(self):
        self.client = Factory().getClient()
        self.review_max_tokens = int(os.getenv('REVIEW_MAX_TOKENS', self.DEFAULT_REVIEW_MAX_TOKENS))

    def call_llm(self, messages: List[Dict[str, Any]]) -> str:
        print(f"向 AI请求, messages: {messages}")
        review_result = self.client.completions(messages=messages)
        print(f"收到 AI 返回结果: {review_result}")
        return review_result

    def review_and_strip_code(self, text: str) -> str:
        if not text:
            print("警告: 内容为空，无法进行评审。")
            return '内容为空，无法进行评审。'

        # 计算tokens数量，如果超过REVIEW_MAX_TOKENS，截断changes_text
        tokens_count = count_tokens(text)
        if tokens_count > self.review_max_tokens:
            text = truncate_text_by_tokens(text, self.review_max_tokens)

        messages = self.get_prompts(text)
        review_result = self.call_llm(messages).strip()
        if review_result.startswith("```markdown") and review_result.endswith("```"):
            return review_result[11:-3].strip()
        return review_result

    @abstractmethod
    def get_prompts(self, text: str) -> List[Dict[str, Any]]:
        """
        根据输入的文本生成用于调用LLM的提示信息。

        Args:
            text (str): 输入的文本内容。

        Returns:
            List[Dict[str, Any]]: 包含提示信息的字典列表。
        """
        raise NotImplementedError
