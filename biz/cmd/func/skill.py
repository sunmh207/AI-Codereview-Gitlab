import os
import subprocess
from datetime import datetime

from biz.cmd.func.base import BaseReviewFunc
from biz.utils.skill_reviewer import SkillReviewer, default_skill_path


class SkillReviewFunc(BaseReviewFunc):
    """
    通过 Claude Code (claude CLI) 运行本地 Agent Skill 对仓库进行代码审查。

    交互式入口，底层复用 biz.utils.skill_reviewer.SkillReviewer。
    适用于手动审查某个本地 git 仓库(`python -m biz.cmd.review` -> 选 5)。
    """

    def __init__(self):
        self.skill_path = None
        self.repo_dir = None
        self.diff_range = None
        self.save_to_file = None

    def _default_repo_dir(self, skill_path: str) -> str:
        """根据 skill 路径推断默认仓库目录(.skills 的上一级)，否则用当前目录。"""
        skill_path = os.path.abspath(skill_path)
        parent = os.path.dirname(skill_path)
        if os.path.basename(parent).lower() == ".skills":
            return os.path.dirname(parent)
        return os.getcwd()

    @staticmethod
    def _is_git_repo(directory: str) -> bool:
        try:
            result = subprocess.run(
                ["git", "-C", directory, "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        except Exception:
            return False

    def parse_arguments(self):
        while True:
            self.skill_path = self.get_user_input("请输入 skill 目录", default=default_skill_path())
            if os.path.isfile(os.path.join(self.skill_path, "SKILL.md")):
                break
            print(f"❌ 未找到 SKILL.md: {os.path.join(self.skill_path, 'SKILL.md')}")

        default_repo = self._default_repo_dir(self.skill_path)
        while True:
            self.repo_dir = self.get_user_input("请输入待审查的代码仓库根目录", default=default_repo)
            if self._is_git_repo(self.repo_dir):
                break
            print(f"❌ 不是有效的 git 仓库: {self.repo_dir}")

        self.diff_range = self.get_user_input(
            "审查范围(git diff 参数, 如 HEAD~1、main...HEAD; 留空=当前未提交改动)", default=""
        )
        self.save_to_file = self.get_user_input(
            "是否将结果保存到 Markdown 文件?(y/n)", default="y"
        ).lower() in ["y", "yes"]

    def _save_result(self, content: str):
        out_dir = os.path.join(os.getcwd(), "log")
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        repo_name = os.path.basename(os.path.normpath(self.repo_dir)) or "repo"
        out_path = os.path.join(out_dir, f"skill_review_{repo_name}_{ts}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n💾 结果已保存至: {out_path}")

    def process(self):
        self.parse_arguments()
        if not self.confirm_action("是否确认开始 Skill 审查?(y/n): "):
            print("用户取消操作，退出程序。")
            return

        print("\n🚀 正在调用 claude CLI 运行 skill 审查(可能需要数分钟)...\n")
        reviewer = SkillReviewer(self.skill_path)
        result = reviewer.review(self.repo_dir, self.diff_range or None)

        print("\n" + "=" * 60)
        print("Skill Review 结果:\n")
        print(result)
        print("=" * 60)

        if self.save_to_file and result:
            self._save_result(result)
