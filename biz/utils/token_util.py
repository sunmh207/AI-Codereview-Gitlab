import tiktoken


def count_tokens(text: str) -> int:
    """
    计算文本的 token 数量。

    Args:
        text (str): 输入文本。

    Returns:
        int: token 数量。
    """
    encoding = tiktoken.get_encoding("cl100k_base")  # 适用于 OpenAI GPT 系列
    return len(encoding.encode(text))


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
    # 获取编码器
    encoding = tiktoken.get_encoding(encoding_name)

    # 将文本编码为 tokens
    tokens = encoding.encode(text)

    # 如果 tokens 数量超过最大限制，则截断
    if len(tokens) > max_tokens:
        truncated_tokens = tokens[:max_tokens]
        truncated_text = encoding.decode(truncated_tokens)
        return truncated_text

    return text

if __name__ == '__main__':
    text = "Hello, world! This is a test text for token counting."
    print(count_tokens(text))  # 输出：11
    print(truncate_text_by_tokens(text, 5))  # 输出："Hello, world!"