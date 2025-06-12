from biz.utils.im.dingtalk import DingTalkNotifier
from biz.utils.im.feishu import FeishuNotifier
from biz.utils.im.webhook import ExtraWebhookNotifier
from biz.utils.im.wecom import WeComNotifier


def send_notification(content, msg_type='text', title="通知", is_at_all=False, project_name=None, url_slug=None,
                      webhook_data: dict={}):
    """
    发送通知消息到配置的平台(钉钉和企业微信)
    :param content: 消息内容
    :param msg_type: 消息类型，支持text和markdown
    :param title: 消息标题(markdown类型时使用)
    :param is_at_all: 是否@所有人
    :param url_slug: 由gitlab服务器的url地址(如:http://www.gitlab.com)转换成的slug格式，如: www_gitlab_com
    :param webhook_data: push event、merge event的数据内容
    """
    # 钉钉推送
    dingtalk_notifier = DingTalkNotifier()
    dingtalk_notifier.send_message(content=content, msg_type=msg_type, title=title, is_at_all=is_at_all,
                                   project_name=project_name, url_slug=url_slug)

    # 企业微信推送
    wecom_notifier = WeComNotifier()
    wecom_notifier.send_message(content=content, msg_type=msg_type, title=title, is_at_all=is_at_all,
                                project_name=project_name, url_slug=url_slug)

    # 飞书推送
    feishu_notifier = FeishuNotifier()
    feishu_notifier.send_message(content=content, msg_type=msg_type, title=title, is_at_all=is_at_all,
                                 project_name=project_name, url_slug=url_slug)

    # 额外自定义webhook通知
    extra_webhook_notifier = ExtraWebhookNotifier()
    system_data = {
        "content": content,
        "msg_type": msg_type,
        "title": title,
        "is_at_all": is_at_all,
        "project_name": project_name,
        "url_slug": url_slug
    }
    extra_webhook_notifier.send_message(system_data=system_data, webhook_data=webhook_data)