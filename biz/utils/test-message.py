import requests

class Developer:
    def __init__(self, name, experience):
        self.name = name
        self.experience = experience
    
    def teach(self, newbie):
        webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=f0387535da12ffb7a0146048c6d6cf20585a0d8addaf9c19197794e4a9758458"

        message = {
            "msgtype": "actionCard",
            "userid_list": "hxxuds",
            "at": {
             "atUserIds": ["hxxuds"]
            },
            "actionCard": {
                "title": "折叠消息示例",
                "text": "### 折叠消息示例\n\n> @hxxuds 这是一条折叠消息\n> 点击下方按钮查看详细内容\n\n---\n\n### 详细内容\n\n这是折叠消息的详细内容。\n\n- 列表项1\n- 列表项2",
                "btnOrientation": "1",
                "btns": [
                    {
                        "title": "查看详情",
                        "actionURL": "http://vmchngit02.riking.net/riking/TestCoderReview/commit/a5b42f6ffc6e3eb2916cb98059b821ebb27d09c9"
                    },
                    {
                        "title": "更多信息",
                        "actionURL": "https://baidu.com"
                    }
                ]
            }
        }

        response = requests.post(webhook_url, json=message)

def main():
    # 创建一个开发者实例
    senior_dev = Developer("张三", "5年")
    
    # 调用teach方法发送消息
    senior_dev.teach("李四")
    print("消息已发送，请检查钉钉群接收情况")

if __name__ == "__main__":
    main()