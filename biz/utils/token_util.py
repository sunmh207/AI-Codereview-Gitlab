import logging
from typing import Optional

import tiktoken

logger = logging.getLogger(__name__)

# 缓存编码器实例
_encoding_cache: Optional[tiktoken.Encoding] = None


def _get_encoding_cached(encoding_name: str = "cl100k_base") -> Optional[tiktoken.Encoding]:
    """
    获取编码器，带缓存和错误处理。

    Args:
        encoding_name: 编码器名称

    Returns:
        编码器实例，如果失败则返回 None
    """
    global _encoding_cache
    if _encoding_cache is not None:
        return _encoding_cache

    try:
        _encoding_cache = tiktoken.get_encoding(encoding_name)
        return _encoding_cache
    except Exception as e:
        logger.warning(f"Failed to load tiktoken encoding '{encoding_name}': {e}")
        return None


def _estimate_tokens_simple(text: str) -> int:
    """
    简单token估算（离线fallback）。
    基于经验：英文约4字符/token，中文约2字符/token。

    Args:
        text: 输入文本

    Returns:
        估算的token数量
    """
    if not text:
        return 0

    # 统计中文字符和英文字符
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars

    # 估算：中文约2字符/token，英文/其他约4字符/token
    estimated_tokens = chinese_chars // 2 + other_chars // 4
    return max(estimated_tokens, 1)


def count_tokens(text: str) -> int:
    """
    计算文本的 token 数量。

    Args:
        text (str): 输入文本。

    Returns:
        int: token 数量。
    """
    encoding = _get_encoding_cached()
    if encoding is not None:
        return len(encoding.encode(text))
    # Offline fallback: 使用简单估算
    return _estimate_tokens_simple(text)


def truncate_text_by_tokens(text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
    """
    根据最大 token 数量截断文本。

    Args:
        text (str): 需要截断的原始文本。
        max_tokens (int): 最大 token 数量。
        encoding_name (str): 使用的编码器名称，默认为 "cl100k_base"。

    Returns:
        str: 截断后的文本。
    """
    encoding = _get_encoding_cached(encoding_name)
    if encoding is not None:
        tokens = encoding.encode(text)
        if len(tokens) > max_tokens:
            truncated_tokens = tokens[:max_tokens]
            return encoding.decode(truncated_tokens)
        return text

    # Offline fallback: 使用字符数估算截断
    if not text:
        return text

    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    # 估算每token对应的字符数
    chars_per_token = 2 if chinese_chars > other_chars else 4
    max_chars = max_tokens * chars_per_token

    if len(text) <= max_chars:
        return text
    return text[:max_chars]

if __name__ == '__main__':
    text = "Hello, world! This is a test text for token counting."
    print(count_tokens(text))  # 输出：11
    print(truncate_text_by_tokens(text, 5))  # 输出："Hello, world!"