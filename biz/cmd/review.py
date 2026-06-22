from dotenv import load_dotenv

from biz.cmd.func.branch import BranchReviewFunc
from biz.cmd.func.complexity import ComplexityReviewFunc
from biz.cmd.func.directory import DirectoryReviewFunc
from biz.cmd.func.mysql import MySQLReviewFunc
from biz.cmd.func.skill import SkillReviewFunc


def welcome_message():
    print("\n欢迎使用 Codebase Review 工具！\n")


def get_func_choice():
    options = {
        "1": ("Review 目录结构规范", DirectoryReviewFunc),
        "2": ("Review 代码分支命名规范", BranchReviewFunc),
        "3": ("Review 代码复杂度", ComplexityReviewFunc),
        "4": ("Review MySQL 数据库表结构", MySQLReviewFunc),
        "5": ("Skill 审查 (Claude Code + code-review-expert)", SkillReviewFunc),
    }

    print("📌 请选择功能:")
    for key, (desc, _) in options.items():
        print(f"{key}. {desc}")

    while True:
        choice = input(f"请输入数字 (1-{len(options)}): ").strip()
        if choice in options:
            return options[choice][1]  # 返回对应的类
        print(f"❌ 无效的选择，请输入 1-{len(options)}")


if __name__ == "__main__":
    load_dotenv("conf/.env")
    welcome_message()

    FuncClass = get_func_choice()  # 获取用户选择的功能类
    func = FuncClass()  # 实例化对应的功能
    func.process()  # 执行功能
