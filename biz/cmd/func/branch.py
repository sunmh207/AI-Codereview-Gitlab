import os
import re
from typing import List, Dict, Any
from urllib.parse import urlparse

from gitlab import Gitlab

from biz.cmd.func.base import LLMReviewFunc


class BranchReviewFunc(LLMReviewFunc):
    """
    对代码分支进行审查。
    """
    SYSTEM_PROMPT = f"""
        你是一位资深的软件架构师，本次任务是对一个代码库的分支名称进行审查，具体要求如下：
        
        ### 具体要求：
        1.命名规范一致性：分支命名是否符合团队或项目定义的命名规范；是否遵循统一的命名风格（如小写字母、连字符分隔等）。
        2.分支命名的可读性：分支名称是否能够清晰地表达其目的或功能；是否使用了容易引起混淆的缩写或术语。
        3.分支命名的功能性：分支名称是否能够准确描述其实现的功能或修复的问题；是否与相关的任务、需求或问题（如 Jira Issue、GitLab Issue 等）关联。
        4.分支命名的唯一性：分支名称是否与现有分支重复或过于相似；对于临时分支，是否包含时间戳或唯一标识以避免冲突。
        5.分支命名的长度：分支名称是否过长，导致难以阅读或操作；是否在描述清晰的前提下尽量保持简短。
        6.分支命名的类型化：是否使用了合适的前缀来区分分支类型；分支类型是否与其实际用途一致；

        ### 输出格式：
        1.请按照以下格式输出review结果：
        2.优点：列出目录结构的优点。
        3.潜在问题：指出目录结构中可能存在的问题。
        4.改进建议：提供具体的优化建议。
        """

    def __init__(self):
        super().__init__()
        self.gitlab_url = None
        self.project_id = None
        self.access_token = os.getenv("GITLAB_ACCESS_TOKEN", None)
        self.user_prompt = None

    def parse_gitlab_url(self, url: str):
        """
        解析 GitLab 项目 URL，提取 gitlab_url 和 project_id。
        """
        parsed_url = urlparse(url)

        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("❌ 无效的 GitLab 项目 URL，请确保 URL 格式正确")

        gitlab_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # 预处理路径，去掉末尾 `/` 和 `.git`
        project_path = parsed_url.path.strip("/").removesuffix(".git")

        # 通过正则匹配项目路径，忽略 `/-/tree/`、`/-/blob/` 之后的部分
        match = re.match(r"^([^/]+/[^/]+)", project_path)
        if not match:
            raise ValueError("❌ 无法提取 GitLab 项目路径，请检查 URL 是否正确")

        return gitlab_url, match.group(1)

    def parse_arguments(self):
        """
        使用交互方式获取用户输入的参数。
        """
        # 获取 GitLab 项目 URL
        while True:
            gitlab_project_url = input(
                "请输入 GitLab 项目的完整 URL (例如 https://gitlab.example.com/root/test): ").strip()
            try:
                self.gitlab_url, self.project_id = self.parse_gitlab_url(gitlab_project_url)
                break
            except ValueError as e:
                print(e)

            # 如果环境变量中没有访问令牌，则提示用户输入
            if not self.access_token:
                while True:
                    self.access_token = input("请输入 GitLab 访问令牌: ").strip()
                    if self.access_token:
                        break
                    print("❌ 访问令牌不能为空")

    def get_prompts(self, text: str) -> List[Dict[str, Any]]:
        self.user_prompt = f"""
            以下是一个代码库的分支列表，请对其进行审查，并给出详细的评价。

            {text}
            """
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.user_prompt},
        ]

    def mask_token(self,token, visible_start=4, visible_end=4, mask_char="*"):
        if len(token) <= visible_start + visible_end:
            return token  # 太短的 token 不脱敏

        masked_part = mask_char * (len(token) - visible_start - visible_end)
        return token[:visible_start] + masked_part + token[-visible_end:]

    def process(self):
        self.parse_arguments()
        print("self.gitlab_url", self.gitlab_url)
        print("self.access_token",self.mask_token(self.access_token))
        print("self.project_id", self.project_id)
        gl = Gitlab(self.gitlab_url, private_token=self.access_token)
        project = gl.projects.get(self.project_id)

        # 3. 获取所有分支
        branches = project.branches.list(all=True)  # all=True 确保获取所有分支
        branch_names = "\n".join([branch.name for branch in branches])

        print("分支列表:\n", branch_names)

        if self.confirm_action("是否确认发送 Review 请求？(y/n): "):
            result = self.review_and_strip_code(branch_names)
            print("Review 结果:\n", result)
        else:
            print("用户取消操作，退出程序。")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("conf/.env")
    func = BranchReviewFunc()
    func.process()
