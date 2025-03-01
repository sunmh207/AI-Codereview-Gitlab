import os
import sys
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from biz.utils.dingtalk import DingTalkNotifier


def test_card_message():
    """
    测试发送钉钉卡片消息
    使用actionCard类型实现更美观的消息展示效果
    """
    print("开始测试钉钉卡片消息推送...")
    
    # 创建钉钉通知器实例
    notifier = DingTalkNotifier(project_name="None")
    
    # 构建卡片消息内容
    title = "钉钉卡片消息测试"
    
    # 创建卡片内容，支持markdown格式
    content = " ### 折叠消息示例\n\n> 这是一条折叠消息\n> 点击下方按钮查看详细内容\n\n---\n\n### 详细内容\n\n这是折叠消息的详细内容。\n\n- 列表项1\n- 列表项2",

    
    # 构建按钮配置
    btns = [
        {
            "title": "查看详情",
            "actionURL": "https://example.com/details"
        },
        {
            "title": "系统监控",
            "actionURL": "https://example.com/monitor"
        }
    ]
    
   
    
    notifier.send_message(content=content,title="Review 通知", msg_type='actionCard',btns=btns)
    
    print("消息已发送，请检查钉钉群接收情况")


if __name__ == "__main__":
    test_card_message()