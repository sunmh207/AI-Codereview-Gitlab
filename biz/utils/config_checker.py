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
    # anthropic 的认证(API Key / Bearer Token)与 URL 在 check_llm_provider 里单独校验
    "anthropic": ["ANTHROPIC_API_MODEL"],
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

    # anthropic 支持两种认证: API Key(x-api-key) 或 Bearer Token(中转网关)，二者有其一即可
    if llm_provider == "anthropic" and not (
        os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
    ):
        missing_keys.append("ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN")

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

def check_skill_connectivity():
    """当审查引擎为 skill 时，自检 claude CLI 与自定义 URL 的连通性。"""
    if os.getenv("REVIEW_ENGINE", "llm") != "skill":
        return
    # 延迟导入，避免非 skill 模式引入额外依赖
    from biz.utils.skill_reviewer import SkillReviewer
    logger.info("REVIEW_ENGINE=skill，正在检查 claude CLI 连通性...")
    try:
        ok, detail = SkillReviewer.healthcheck()
    except Exception as e:
        logger.error(f"claude CLI 连通性自检异常: {e}")
        return
    if ok:
        logger.info(f"claude CLI 连通正常: {detail}")
    else:
        logger.error(f"claude CLI 连通性自检失败: {detail}")

def check_config():
    """主检查入口"""
    logger.info("开始检查配置项...")
    check_env_vars()
    check_llm_provider()
    check_llm_connectivity()
    check_skill_connectivity()
    logger.info("配置项检查完成。")