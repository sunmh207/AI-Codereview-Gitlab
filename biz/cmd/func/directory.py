import os
from pathlib import Path
from typing import List, Dict, Any

from pathspec import PathSpec, GitIgnorePattern

from biz.cmd.func.base import LLMReviewFunc
from biz.utils.dir_util import get_directory_tree


class DirectoryReviewFunc(LLMReviewFunc):
    """
    对项目的目录结构进行审查的功能。
    """
    SUPPORTED_LANGUAGES = ["python", "java", "php", "vue"]
    SYSTEM_PROMPT = f"""
        你是一位资深的软件架构师，本次任务是对一个代码库进行审查，具体要求如下：
        ### 具体要求：
        1.组织逻辑：评估目录结构是否清晰，是否符合常见的项目组织规范（如MVC、分层架构等）。
        2.命名规范性：检查目录和文件的命名是否清晰、一致，是否符合命名约定（如小写字母、短横线分隔等）。
        3.模块化程度：评估代码是否按功能或模块合理划分，是否存在过度耦合或冗余。
        4.可维护性：分析目录结构是否易于扩展和维护，是否适合团队协作。
        5.改进建议：针对发现的问题，提出具体的优化建议。

        ### 输出格式：
        1.请按照以下格式输出review结果：
        2.优点：列出目录结构的优点。
        3.潜在问题：指出目录结构中可能存在的问题。
        4.改进建议：提供具体的优化建议。
        """

    def __init__(self):
        super().__init__()
        self.language = None
        self.directory = None
        self.max_depth = None
        self.only_dirs = None
        self.user_prompt = None

    def validate_directory(self, directory):
        """
        验证用户输入的目录是否存在。
        :param directory: 用户输入的目录路径
        :return: 如果目录存在返回 True，否则返回 False
        """
        try:
            return Path(directory).resolve().is_dir()
        except Exception:
            return False

    def validate_language_choice(self, choice):
        """
        验证用户输入的数字是否有效。
        :param choice: 用户输入的数字
        :return: 如果有效返回 True，否则返回 False
        """
        return choice.isdigit() and 1 <= int(choice) <= len(self.SUPPORTED_LANGUAGES)

    def parse_arguments(self):
        """
        使用交互方式获取用户输入的参数。
        """
        # 显示语言选项
        print("请选择开发语言:")
        for index, language in enumerate(self.SUPPORTED_LANGUAGES, start=1):
            print(f"{index}. {language}")

        # 获取开发语言
        while True:
            choice = input(f"请输入数字 (1-{len(self.SUPPORTED_LANGUAGES)}): ").strip()
            if self.validate_language_choice(choice):
                self.language = self.SUPPORTED_LANGUAGES[int(choice) - 1]  # 获取对应的语言
                break
            print(f"❌ 无效的选择，请输入 1 到 {len(self.SUPPORTED_LANGUAGES)} 之间的数字")

        # 获取项目目录
        while True:
            self.directory = input("请输入代码项目的根目录路径: ").strip()
            if self.validate_directory(self.directory):
                break
            print("❌ 目录不存在，请输入有效路径")

        self.max_depth = self.get_user_input("请输入目录树的最大深度", default=3, input_type=int)
        self.only_dirs = self.get_user_input("是否仅获取目录？(y/n)", default="y").lower() in ["y", "yes"]

    def load_gitignore_patterns(self):
        """加载 .gitignore 规则"""
        gitignore_path = os.path.join(self.directory, ".gitignore")

        if not os.path.exists(gitignore_path):
            return None  # 没有 .gitignore 文件，则不做忽略处理

        with open(gitignore_path, "r", encoding="utf-8") as f:
            patterns = f.readlines()

        return PathSpec.from_lines(GitIgnorePattern, patterns)

    def get_prompts(self, text: str) -> List[Dict[str, Any]]:
        self.user_prompt = f"""
            以下是一个 {self.language} 代码库，请对其进行审查，并给出详细的评价。

            目录结构：
            {text}
            """
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.user_prompt},
        ]

    def process(self):
        self.parse_arguments()
        ignore_spec = self.load_gitignore_patterns()

        directory_structure = get_directory_tree(
            self.directory, ignore_spec, max_depth=self.max_depth, only_dirs=self.only_dirs
        )
        print("目录结构:\n", directory_structure)

        if self.confirm_action("是否确认发送 Review 请求？(y/n): "):
            result = self.review_and_strip_code(directory_structure)
            print("Review 结果:\n", result)
        else:
            print("用户取消操作，退出程序。")
