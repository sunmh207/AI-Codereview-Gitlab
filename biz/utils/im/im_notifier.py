from biz.utils.im.dingtalk import DingTalkNotifier
from biz.utils.im.feishu import FeishuNotifier
from biz.utils.im.wecom import WeComNotifier


def send_notification(content, msg_type='text', title="通知", is_at_all=False, project_name=None):
    """
    发送通知消息到配置的平台(钉钉和企业微信)
    :param content: 消息内容
    :param msg_type: 消息类型，支持text和markdown
    :param title: 消息标题(markdown类型时使用)
    :param is_at_all: 是否@所有人
    """
    # 钉钉推送
    notifier = DingTalkNotifier()
    notifier.send_message(content=content, msg_type=msg_type, title=title, is_at_all=is_at_all,
                          project_name=project_name)

    # 企业微信推送
    wecom_notifier = WeComNotifier()
    wecom_notifier.send_message(content=content, msg_type=msg_type, title=title, is_at_all=is_at_all,
                                project_name=project_name)

    # 飞书推送
    feishu_notifier = FeishuNotifier()
    feishu_notifier.send_message(content=content, msg_type=msg_type, title=title, is_at_all=is_at_all,
                                 project_name=project_name)
