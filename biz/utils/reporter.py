from typing import Dict, Optional

from biz.llm.factory import Factory


class Reporter:
    def __init__(self, config: Optional[Dict[str, str]] = None):
        """
        初始化报告生成器
        :param config: 项目专属配置字典
        """
        self.client = Factory().getClient(config=config)

    def generate_report(self, data: str) -> str:
        # 根据data生成报告
        return self.client.completions(
            messages=[
                {"role": "user", "content": f"下面是以json格式记录员工代码提交信息。请总结这些信息，生成每个员工的工作日报摘要。员工姓名直接用json内容中的author属性值，不要进行转换。特别要求:以Markdown格式返回。\n{data}"},
            ],
        )
