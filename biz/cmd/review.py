from dotenv import load_dotenv

from biz.cmd.func.branch import BranchReviewFunc
from biz.cmd.func.complexity import ComplexityReviewFunc
from biz.cmd.func.directory import DirectoryReviewFunc
from biz.utils.i18n import get_translator

_ = get_translator()

def welcome_message():
    print(_("\n欢迎使用 Codebase Review 工具！\n"))


def get_func_choice():
    _ = get_translator()
    options = {
        "1": (_("Review 目录结构规范"), DirectoryReviewFunc),
        "2": (_("Review 代码分支命名规范"), BranchReviewFunc),
        "3": (_("Review 代码复杂度"), ComplexityReviewFunc),
    }

    print(_("📌 请选择功能:"))
    for key, (desc, _) in options.items():
        print(f"{key}. {desc}")

    while True:
        choice = input(_("请输入数字 (1-3): ")).strip()
        if choice in options:
            return options[choice][1]  # 返回对应的类
        print(_("❌ 无效的选择，请输入 1-3"))


if __name__ == "__main__":
    load_dotenv("conf/.env")
    welcome_message()

    FuncClass = get_func_choice()  # 获取用户选择的功能类
    func = FuncClass()  # 实例化对应的功能
    func.process()  # 执行功能
