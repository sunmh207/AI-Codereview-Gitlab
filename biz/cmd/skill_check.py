"""
Skill / claude CLI 连通性自检。

部署后快速验证：claude CLI 是否装好、自定义 API URL / 认证 / 模型是否真正跑通。

用法:
    python -m biz.cmd.skill_check
"""
import sys

from dotenv import load_dotenv

from biz.utils.skill_reviewer import SkillReviewer, default_skill_path


def main() -> int:
    # override=True: 让 conf/.env 成为本检查的权威来源，
    # 避免宿主已 export 的 ANTHROPIC_* 遮蔽 .env 里的配置(load_dotenv 默认不覆盖)。
    load_dotenv("conf/.env", override=True)

    print("==== Skill / claude CLI 连通性自检 ====")
    print(f"skill 路径   : {default_skill_path()}")

    env = SkillReviewer._build_env()
    print(f"API URL      : {env.get('ANTHROPIC_BASE_URL', '(默认官方)')}")
    print(f"认证方式     : {'Bearer Token' if env.get('ANTHROPIC_AUTH_TOKEN') else ('API Key' if env.get('ANTHROPIC_API_KEY') else '未配置')}")
    print(f"模型         : {env.get('ANTHROPIC_MODEL', '(CLI 默认)')}")
    print("正在验证 claude CLI 安装 + 网关连通(SDK 直连, 通常数秒)...\n")

    ok, detail = SkillReviewer.healthcheck()
    print(("[OK] " if ok else "[FAIL] ") + detail)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
