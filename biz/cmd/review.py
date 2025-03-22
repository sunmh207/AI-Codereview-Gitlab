import os
from pathlib import Path

from dotenv import load_dotenv
from pathspec import PathSpec, GitIgnorePattern

from biz.utils.code_reviewer import CodeBaseReviewer
from biz.utils.dir_util import get_directory_tree
from biz.utils.i18n import get_translator
from biz.utils.log import logger
from biz.utils.token_util import count_tokens, truncate_text_by_tokens

_ = get_translator()

SUPPORTED_LANGUAGES = ["python", "java", "php", "vue"]


def validate_language_choice(choice):
    """
    验证用户输入的数字是否有效。
    :param choice: 用户输入的数字
    :return: 如果有效返回 True，否则返回 False
    """
    return choice.isdigit() and 1 <= int(choice) <= len(SUPPORTED_LANGUAGES)


def validate_directory(directory):
    """
    验证用户输入的目录是否存在。
    :param directory: 用户输入的目录路径
    :return: 如果目录存在返回 True，否则返回 False
    """
    return Path(directory).is_dir()


def get_user_input(prompt: str, default=None, input_type=str):
    """
    获取用户输入，支持默认值和类型转换。

    Args:
        prompt (str): 提示信息。
        default: 默认值。
        input_type: 输入值的类型（如 int, str, bool 等）。

    Returns:
        用户输入的值或默认值。
    """
    user_input = input(f"{prompt} (默认: {default}): ").strip()
    if not user_input:
        return default
    try:
        return input_type(user_input)
    except ValueError:
        print(_("输入无效，请输入 {} 类型的值。").format(input_type.__name__))
        return get_user_input(prompt, default, input_type)


def parse_arguments():
    """
    使用交互方式获取用户输入，并返回语言和目录。
    :return: 语言和目录的元组 (language, directory)
    """
    # 显示语言选项
    print(_("请选择开发语言:"))
    for index, language in enumerate(SUPPORTED_LANGUAGES, start=1):
        print(f"{index}. {language}")

    # 获取开发语言
    while True:
        choice = input(_("请输入数字 (1-{}): ").format(len(SUPPORTED_LANGUAGES)).strip())
        if validate_language_choice(choice):
            language = SUPPORTED_LANGUAGES[int(choice) - 1]  # 获取对应的语言
            break
        print(_("❌ 无效的选择，请输入 1 到 {} 之间的数字").format(len(SUPPORTED_LANGUAGES)))

        # 获取项目目录
    while True:
        directory = input(_("请输入代码项目的根目录路径: ")).strip()
        if validate_directory(directory):
            break
        print(_("❌ 目录不存在，请输入有效路径"))

    max_depth = get_user_input(_("请输入目录树的最大深度"), default=3, input_type=int)
    only_dirs = get_user_input(_("是否仅获取目录？(y/n)"), default="y").lower() in ["y", "yes"]

    return language, directory, max_depth, only_dirs


def load_gitignore_patterns(directory):
    """加载 .gitignore 规则"""
    gitignore_path = os.path.join(directory, ".gitignore")

    if not os.path.exists(gitignore_path):
        return None  # 没有 .gitignore 文件，则不做忽略处理

    with open(gitignore_path, "r", encoding="utf-8") as f:
        patterns = f.readlines()

    return PathSpec.from_lines(GitIgnorePattern, patterns)


def review_code(text: str) -> str:
    # 如果超长，取前REVIEW_MAX_TOKENS个token
    review_max_tokens = int(os.getenv('REVIEW_MAX_TOKENS', 10000))
    # 如果changes为空,打印日志
    if not text:
        logger.info(_('代码为空, diffs_text = {}').format(str(text)))
        return _('代码为空')

    # 计算tokens数量，如果超过REVIEW_MAX_TOKENS，截断changes_text
    tokens_count = count_tokens(text)
    if tokens_count > review_max_tokens:
        text = truncate_text_by_tokens(text, review_max_tokens)

    review_result = CodeBaseReviewer().review_code(text).strip()
    if review_result.startswith("```markdown") and review_result.endswith("```"):
        return review_result[11:-3].strip()
    return review_result


def confirm_action(prompt: str) -> bool:
    while True:
        user_input = input(prompt).strip().lower()
        if user_input in ["y", "yes"]:
            return True
        elif user_input in ["n", "no"]:
            return False
        else:
            print(_("请输入 'y' 或 'n' 确认。"))


if __name__ == "__main__":
    load_dotenv("conf/.env")

    language, directory, max_depth, only_dirs = parse_arguments()
    ignore_spec = load_gitignore_patterns(directory)
    directory_structure = get_directory_tree(directory, ignore_spec, max_depth=max_depth, only_dirs=only_dirs)
    print(_("目录结构:\n"), directory_structure)

    # 用户确认
    if confirm_action(_("是否确认发送 Review 请求？(y/n): ")):
        # 初始化 CodeBaseReviewer
        reviewer = CodeBaseReviewer()

        # 执行 CodeReview
        result = reviewer.review_code(language, directory_structure)
        print(_("Review 结果:\n"), result)
    else:
        print(_("用户取消操作，退出程序。"))
