from core.llm.factory import Factory
from biz.utils.i18n import get_translator
_ = get_translator()

class Reporter:
    def __init__(self):
        self.client = Factory().getClient()

    def generate_report(self, data: str) -> str:
        # 根据data生成报告
        return self.client.completions(
            messages=[
                {"role": "user", "content": _("下面是以json格式记录员工代码提交信息。请总结这些信息，生成每个员工的工作日报摘要。员工姓名直接用json内容中的author属性值，不要进行转换。特别要求:以Markdown格式返回。\n{}").format(data)},
            ],
        )
