import requests
import os
from biz.utils.log import logger


class FeishuNotifier:
    def __init__(self, webhook_url=None, project_config=None):
        """
        初始化飞书通知器
        :param webhook_url: 飞书机器人webhook地址
        :param project_config: 项目专属配置字典
        """
        self.project_config = project_config or {}
        # 优先从 project_config 获取，如果没有则降级到 os.environ
        self.default_webhook_url = webhook_url or self.project_config.get('FEISHU_WEBHOOK_URL', '') or os.environ.get('FEISHU_WEBHOOK_URL', '')
        self.enabled = self._get_enabled_status('FEISHU_ENABLED', '0')

    def _get_enabled_status(self, config_key, default_value='0'):
        """获取启用状态，修复逻辑错误"""
        enabled = self.project_config.get(config_key)
        if enabled is None:
            enabled = os.environ.get(config_key, default_value)
        return enabled == '1'

    def _get_webhook_url(self, project_name=None, url_slug=None, msg_category=None):
        """
        获取项目对应的 Webhook URL
        :param project_name: 项目名称
        :param url_slug: URL slug
        :param msg_category: 消息类别（如：daily_report），用于区分不同场景的webhook
        :return: Webhook URL
        :raises ValueError: 如果未找到 Webhook URL
        """
        # 如果指定了消息类别（如日报），只使用全局默认的专用 webhook，不查找项目级别配置
        if msg_category:
            category_webhook_key = f"FEISHU_WEBHOOK_URL_{msg_category.upper()}"
            # 优先从 project_config 获取，如果没有则降级到 os.environ
            category_webhook_url = self.project_config.get(category_webhook_key) or os.environ.get(category_webhook_key)
            if category_webhook_url:
                return category_webhook_url
            # 如果没有配置专用webhook，降级使用默认webhook
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError(f"未设置消息类别 '{msg_category}' 的专用飞书 Webhook URL，且未设置默认的飞书 Webhook URL。")
        
        # 如果未提供 project_name，直接返回默认的 Webhook URL
        if not project_name:
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError("未提供项目名称，且未设置默认的 飞书 Webhook URL。")

        # 构造目标键
        target_key_project = f"FEISHU_WEBHOOK_URL_{project_name.upper()}"
        target_key_url_slug = f"FEISHU_WEBHOOK_URL_{url_slug.upper()}" if url_slug else None

        # 遍历项目配置
        for config_key, config_value in self.project_config.items():
            config_key_upper = config_key.upper()
            if config_key_upper == target_key_project:
                return config_value  # 找到项目名称对应的 Webhook URL，直接返回
            if target_key_url_slug and config_key_upper == target_key_url_slug:
                return config_value  # 找到 GitLab URL 对应的 Webhook URL，直接返回

        # 如果未找到匹配的配置项，降级使用全局的 Webhook URL
        if self.default_webhook_url:
            return self.default_webhook_url

        # 如果既未找到匹配项，也没有默认值，抛出异常
        raise ValueError(f"未找到项目 '{project_name}' 对应的 Feishu Webhook URL，且未设置默认的 Webhook URL。")

    def send_message(self, content, msg_type='text', title=None, is_at_all=False, project_name=None, url_slug=None, msg_category=None):
        """
        发送飞书消息
        :param content: 消息内容
        :param msg_type: 消息类型，支持text和markdown
        :param title: 消息标题(markdown类型时使用)
        :param is_at_all: 是否@所有人
        :param project_name: 项目名称
        :param url_slug: URL slug
        :param msg_category: 消息类别（如：daily_report），用于区分不同场景的webhook
        """
        if not self.enabled:
            logger.info("飞书推送未启用")
            return

        try:
            post_url = self._get_webhook_url(project_name=project_name, url_slug=url_slug, msg_category=msg_category)
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
                logger.error(f"飞书消息发送失败! webhook_url:{post_url}, error_msg:{response.text}")
                return

            result = response.json()
            if result.get('msg') != "success":
                logger.error(f"发送飞书消息失败! webhook_url:{post_url},errmsg:{result}")
            else:
                logger.info(f"飞书消息发送成功! webhook_url:{post_url}")

        except Exception as e:
            logger.error(f"飞书消息发送失败! ", e)
