import os
import shutil
import subprocess

from biz.utils.log import logger


def default_skill_path() -> str:
    """默认 skill 路径：随镜像打包在 conf/skills/code-review-expert，可用环境变量覆盖。"""
    return os.getenv(
        "REVIEW_SKILL_PATH",
        os.path.join(os.getcwd(), "conf", "skills", "code-review-expert"),
    )


class SkillReviewer:
    """
    通过 Claude Code (claude CLI) 以 headless 模式运行本地 Agent Skill 审查一个本地 git 仓库。

    这是 agentic 审查：claude 会读取 SKILL.md 并按其 workflow 执行(自动按需加载
    references/*.md、运行 git diff、读取相邻代码)，因此 repo_dir 必须是真实的 git 工作区。

    前置条件：
    - 容器/主机已安装 claude CLI(`claude --version` 可用)。
    - 已通过 ANTHROPIC_API_KEY 完成认证(服务器无法交互式 /login)。
    """

    def __init__(self, skill_path: str = None):
        self.skill_path = os.path.abspath(skill_path or default_skill_path())
        skill_md = os.path.join(self.skill_path, "SKILL.md")
        if not os.path.isfile(skill_md):
            raise FileNotFoundError(f"未找到 SKILL.md: {skill_md}")

    @staticmethod
    def _find_git_bash() -> str:
        """在 Windows 上定位 git-bash 的 bash.exe(headless claude 必需; Linux 不需要)。"""
        env_path = os.getenv("CLAUDE_CODE_GIT_BASH_PATH")
        if env_path and os.path.isfile(env_path):
            return env_path
        candidates = []
        git_exe = shutil.which("git")
        if git_exe:
            git_root = os.path.dirname(os.path.dirname(git_exe))
            candidates.append(os.path.join(git_root, "bin", "bash.exe"))
        candidates += [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
            r"D:\software\Git\bin\bash.exe",
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        return ""

    def _build_prompt(self, diff_range: str = None) -> str:
        skill_md = os.path.join(self.skill_path, "SKILL.md")
        references_dir = os.path.join(self.skill_path, "references")
        if diff_range:
            scope = f"`git diff {diff_range}` 的改动"
        else:
            scope = "当前仓库未提交的改动(git status / git diff)"
        return (
            f"请阅读位于 `{skill_md}` 的 Code Review skill, 并严格按照其 Workflow 执行, "
            f"对本仓库中 {scope} 进行代码审查。\n"
            f"按 skill 指引按需加载 `{references_dir}` 下对应的 checklist 文件。\n"
            f"这是一次只读审查(review-only): 请勿修改任何文件, 也不要在最后询问是否实施修复, "
            f"直接输出 skill 第 11 节定义的完整 Markdown 审查报告即可。\n\n"
            f"⚠️ 最重要的要求: 整份审查报告必须用【简体中文】撰写——所有标题、问题描述、"
            f"修复建议、总结全部用中文, 绝对不要用英文写正文。仅 P0/P1/P2/P3 等级标识、"
            f"文件路径:行号、代码片段、APPROVE/REQUEST_CHANGES/COMMENT 枚举值保持原样。"
        )

    @staticmethod
    def _is_placeholder(value: str) -> bool:
        """判断是否为 .env.dist 里的占位值(如 xxxx)或空值。"""
        return not value or value.strip().lower() in ("", "xxxx", "xxx")

    @classmethod
    def _build_env(cls) -> dict:
        """
        构造 claude CLI 子进程环境变量。

        关键: 把项目 SDK 风格的 ANTHROPIC_API_* 自动映射成 claude CLI 认的变量名，
        使自定义 API URL / Key / 模型对 skill(CLI) 这条路也生效——用户只需在 .env 配一套。
        项目配置(ANTHROPIC_API_*)优先级最高，覆盖宿主可能已存在的 CLI 同义变量，
        确保 .env 里配的自定义 URL 一定生效。
        """
        env = os.environ.copy()

        # 自定义 API URL: SDK 用 ANTHROPIC_API_BASE_URL, CLI 用 ANTHROPIC_BASE_URL
        base_url = env.get("ANTHROPIC_API_BASE_URL")
        if cls._is_placeholder(base_url):
            base_url = env.get("ANTHROPIC_BASE_URL")  # 回退到宿主已有的 CLI 变量
        if not cls._is_placeholder(base_url):
            env["ANTHROPIC_BASE_URL"] = base_url

        # 认证: 优先显式的 bearer token(部分中转网关需要), 否则用 API Key
        auth_token = env.get("ANTHROPIC_AUTH_TOKEN")
        if not cls._is_placeholder(auth_token):
            env["ANTHROPIC_AUTH_TOKEN"] = auth_token
        api_key = env.get("ANTHROPIC_API_KEY")
        if not cls._is_placeholder(api_key):
            env["ANTHROPIC_API_KEY"] = api_key

        # 模型: SDK 用 ANTHROPIC_API_MODEL, CLI 用 ANTHROPIC_MODEL
        model = env.get("ANTHROPIC_API_MODEL")
        if cls._is_placeholder(model):
            model = env.get("ANTHROPIC_MODEL")
        if not cls._is_placeholder(model):
            env["ANTHROPIC_MODEL"] = model

        # Windows: headless claude 需要 git-bash
        if os.name == "nt" and not env.get("CLAUDE_CODE_GIT_BASH_PATH"):
            bash_path = cls._find_git_bash()
            if bash_path:
                env["CLAUDE_CODE_GIT_BASH_PATH"] = bash_path
        return env

    def review(self, repo_dir: str, diff_range: str = None) -> str:
        """对 repo_dir 运行 skill 审查，返回 Markdown 文本。"""
        claude_bin = shutil.which("claude") or "claude"
        cmd = [
            claude_bin,
            "-p",
            self._build_prompt(diff_range),
            "--output-format",
            "text",
            "--permission-mode",
            "bypassPermissions",
        ]

        env = self._build_env()
        model = env.get("ANTHROPIC_MODEL")
        if model:
            # 显式传 --model，兼容性优于仅依赖环境变量
            cmd += ["--model", model]

        logger.info(f"调用 claude CLI 运行 skill 审查: repo={repo_dir}, skill={self.skill_path}, range={diff_range}")
        result = subprocess.run(
            cmd,
            cwd=repo_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        combined = f"{stdout}\n{stderr}"
        if "Not logged in" in combined or "Please run /login" in combined:
            raise RuntimeError(
                "claude CLI 未登录。服务器部署请在 conf/.env 配置 ANTHROPIC_API_KEY。"
            )
        if result.returncode != 0:
            raise RuntimeError(f"claude CLI 执行失败(exit={result.returncode}): {stderr or stdout}")
        return stdout

    @classmethod
    def healthcheck(cls, timeout: int = 60) -> tuple:
        """
        部署后连通性自检(不依赖具体 skill 文件)：
          1) claude CLI 是否安装(claude --version)
          2) 经映射后的自定义 URL / 认证 / 模型 / beta 能否连通

        第 2 步用 SDK 直连同一网关探测，而非 `claude -p`：CLI 对 5xx 会自动重试退避，
        会把真实错误(如 503/400/401)拖成无意义的超时；SDK 几秒内返回真实 HTTP 状态，
        更符合“快速验证”的目标。CLI 与 SDK 走同一 URL/认证/模型，SDK 通即代表该路径可用。

        返回 (ok: bool, detail: str)。
        """
        claude_bin = shutil.which("claude") or "claude"
        env = cls._build_env()
        base = env.get("ANTHROPIC_BASE_URL", "(默认官方 https://api.anthropic.com)")
        model = env.get("ANTHROPIC_MODEL")
        betas = env.get("ANTHROPIC_BETAS", "(无)")

        # 1) CLI 是否安装
        try:
            ver = subprocess.run(
                [claude_bin, "--version"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", env=env, timeout=15,
            )
        except FileNotFoundError:
            return False, "未找到 claude CLI，请确认镜像内已安装 @anthropic-ai/claude-code。"
        except Exception as e:
            return False, f"执行 claude --version 失败: {e}"
        if ver.returncode != 0:
            return False, f"claude --version 失败: {(ver.stderr or ver.stdout).strip()}"
        version = (ver.stdout or "").strip()

        # 2) SDK 直连网关探测(快速、暴露真实 HTTP 错误)
        try:
            from biz.llm.client.anthropic import AnthropicClient
            client = AnthropicClient()
            resp = client.completions(messages=[{"role": "user", "content": "Reply with exactly: OK"}])
        except Exception as e:
            return False, (
                f"claude {version} 已安装，但网关连通失败"
                f"(URL={base}, model={model or '默认'}, betas={betas}): {type(e).__name__}: {str(e)[:200]}"
            )
        return True, (
            f"claude {version} 已安装且网关连通正常。"
            f"URL={base}, model={model or '默认'}, betas={betas}, 响应={str(resp)[:40]!r}"
        )
