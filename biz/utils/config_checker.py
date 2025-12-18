import os

from dotenv import load_dotenv

from biz.llm.factory import Factory
from biz.utils.log import logger

# 指定环境变量文件路径
ENV_FILE_PATH = "conf/.env"
load_dotenv(ENV_FILE_PATH)


REQUIRED_ENV_VARS = [
    "LLM_PROVIDER",
]

# 允许的 LLM 供应商
LLM_PROVIDERS = { "anthropic", "zhipuai", "openai", "deepseek", "ollama", "qwen" }

# 每种供应商必须配置的键
LLM_REQUIRED_KEYS = {
    "anthropic": ["ANTHROPIC_API_KEY", "ANTHROPIC_API_BASE_URL", "ANTHROPIC_API_MODEL"],
    "zhipuai": ["ZHIPUAI_API_KEY", "ZHIPUAI_API_MODEL"],
    "openai": ["OPENAI_API_KEY", "OPENAI_API_MODEL"],
    "deepseek": ["DEEPSEEK_API_KEY", "DEEPSEEK_API_MODEL"],
    "ollama": ["OLLAMA_API_BASE_URL", "OLLAMA_API_MODEL"],
    "qwen": ["QWEN_API_KEY", "QWEN_API_MODEL"],
}


def check_env_vars():
    """检查环境变量"""
    missing_vars = [var for var in REQUIRED_ENV_VARS if var not in os.environ]
    if missing_vars:
        logger.warning(f"缺少环境变量: {', '.join(missing_vars)}")
    else:
        logger.info("所有必要的环境变量均已设置。")


def check_llm_provider():
    """检查 LLM 供应商的配置"""
    llm_provider = os.getenv("LLM_PROVIDER")

    if not llm_provider:
        logger.error("LLM_PROVIDER 未设置！")
        return

    if llm_provider not in LLM_PROVIDERS:
        logger.error(f"LLM_PROVIDER 值错误，应为 {LLM_PROVIDERS} 之一。")
        return

    required_keys = LLM_REQUIRED_KEYS.get(llm_provider, [])
    missing_keys = [key for key in required_keys if not os.getenv(key)]

    if missing_keys:
        logger.error(f"当前 LLM 供应商为 {llm_provider}，但缺少必要的环境变量: {', '.join(missing_keys)}")
    else:
        logger.info(f"LLM 供应商 {llm_provider} 的配置项已设置。")

def check_llm_connectivity():
    client = Factory().getClient()
    logger.info(f"正在检查 LLM 供应商的连接...")
    if client.ping():
        logger.info("LLM 可以连接成功。")
    else:
        logger.error("LLM连接可能有问题，请检查配置项。")

def check_config():
    """主检查入口"""
    logger.info("开始检查配置项...")
    check_env_vars()
    check_llm_provider()
    check_llm_connectivity()
    logger.info("配置项检查完成。")