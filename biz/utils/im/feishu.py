import requests
import os
from biz.utils.log import logger
from biz.utils.i18n import get_translator
_ = get_translator()

class FeishuNotifier:
    def __init__(self, webhook_url=None):
        """
        初始化飞书通知器
        :param webhook_url: 飞书机器人webhook地址
        """
        self.default_webhook_url = webhook_url or os.environ.get('FEISHU_WEBHOOK_URL', '')
        self.enabled = os.environ.get('FEISHU_ENABLED', '0') == '1'

    def _get_webhook_url(self, project_name=None, url_base=None):
        """
        获取项目对应的 Webhook URL
        :param project_name: 项目名称
        :return: Webhook URL
        :raises ValueError: 如果未找到 Webhook URL
        """
        # 如果未提供 project_name，直接返回默认的 Webhook URL
        if not project_name:
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError(_("未提供项目名称，且未设置默认的 飞书 Webhook URL。"))

        # 遍历所有环境变量（忽略大小写），找到项目对应的 Webhook URL
        target_key = f"FEISHU_WEBHOOK_URL_{project_name.upper()}"
        for env_key, env_value in os.environ.items():
            if env_key.upper() == target_key:
                return env_value  # 找到匹配项，直接返回
            
        # url_base 优先级次之
        target_key_url_base = f"WECOM_WEBHOOK_URL_{url_base.upper()}"
        for env_key, env_value in os.environ.items():
            if target_key_url_base !=None and  env_key.upper() == target_key_url_base:
                return env_value  # 找到匹配项，直接返回

        # 如果未找到匹配的环境变量，降级使用全局的 Webhook URL
        if self.default_webhook_url:
            return self.default_webhook_url

        # 如果既未找到匹配项，也没有默认值，抛出异常
        raise ValueError(_("未找到项目 '{project_name}' 对应的 Feishu Webhook URL，且未设置默认的 Webhook URL。"))

    def send_message(self, content, msg_type='text', title=None, is_at_all=False, project_name=None, url_base=None):
        """
        发送飞书消息
        :param content: 消息内容
        :param msg_type: 消息类型，支持text和markdown
        :param title: 消息标题(markdown类型时使用)
        :param is_at_all: 是否@所有人
        :param project_name: 项目名称
        """
        if not self.enabled:
            logger.info(_("飞书推送未启用"))
            return

        try:
            post_url = self._get_webhook_url(project_name=project_name, url_base=url_base)
            if msg_type == 'markdown':
                data = {
                    "msg_type": "interactive",
                    "card": {
                        "schema": "2.0",
                        "config": {
                            "update_multi": True,
                            "style": {
                                "text_size": {
                                    "normal_v2": {
                                        "default": "normal",
                                        "pc": "normal",
                                        "mobile": "heading"
                                    }
                                }
                            }
                        },
                        "body": {
                            "direction": "vertical",
                            "padding": "12px 12px 12px 12px",
                            "elements": [
                                {
                                    "tag": "markdown",
                                    "content": content,
                                    "text_align": "left",
                                    "text_size": "normal_v2",
                                    "margin": "0px 0px 0px 0px"
                                }
                            ]
                        },
                        "header": {
                            "title": {
                                "tag": "plain_text",
                                "content": title
                            },
                            "template": "blue",
                            "padding": "12px 12px 12px 12px"
                        }
                    }
                }
            else:
                data = {
                    "msg_type": "text",
                    "content": {
                        "text": content
                    },
                }

            response = requests.post(
                url=post_url,
                json=data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code != 200:
                logger.error(_("飞书消息发送失败! webhook_url: {post_url}, error_msg: {post_url}").format(post_url=post_url, error_msg=response.text))
                return

            result = response.json()
            if result.get('msg') != "success":
                logger.error(_("发送飞书消息失败! webhook_url: {post_url}, errmsg: {result}").format(post_url=post_url, result=result))
            else:
                logger.info(_("飞书消息发送成功! webhook_url: {post_url}").format(post_url=post_url))

        except Exception as e:
            logger.error(_("飞书消息发送失败!"), e)
