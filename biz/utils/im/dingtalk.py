import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse

import requests

from biz.utils.log import logger


class DingTalkNotifier:
    def __init__(self, webhook_url=None, project_config=None):
        """
        初始化钉钉通知器
        :param webhook_url: 钉钉机器人webhook地址
        :param project_config: 项目专属配置字典
        """
        self.project_config = project_config or {}
        # 优先从 project_config 获取，如果没有则降级到 os.environ
        self.enabled = (self.project_config.get('DINGTALK_ENABLED', '0') or os.environ.get('DINGTALK_ENABLED', '0')) == '1'
        self.default_webhook_url = webhook_url or self.project_config.get('DINGTALK_WEBHOOK_URL') or os.environ.get('DINGTALK_WEBHOOK_URL')

    def _get_webhook_url(self, project_name=None, url_slug=None, msg_category=None):
        """
        获取项目对应的 Webhook URL
        :param project_name: 项目名称
        :param url_slug: 由 gitlab 项目的 url 转换而来的 slug
        :param msg_category: 消息类别（如：daily_report），用于区分不同场景的webhook
        :return: Webhook URL
        :raises ValueError: 如果未找到 Webhook URL
        """
        # 如果指定了消息类别（如日报），只使用全局默认的专用 webhook，不查找项目级别配置
        if msg_category:
            category_webhook_key = f"DINGTALK_WEBHOOK_URL_{msg_category.upper()}"
            # 优先从 project_config 获取，如果没有则降级到 os.environ
            category_webhook_url = self.project_config.get(category_webhook_key) or os.environ.get(category_webhook_key)
            if category_webhook_url:
                return category_webhook_url
            # 如果没有配置专用webhook，降级使用默认webhook
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError(f"未设置消息类别 '{msg_category}' 的专用钉钉 Webhook URL，且未设置默认的钉钉 Webhook URL。")
        
        # 如果未提供 project_name，直接返回默认的 Webhook URL
        if not project_name:
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError("未提供项目名称，且未设置默认的钉钉 Webhook URL。")

        # 构造目标键
        target_key_project = f"DINGTALK_WEBHOOK_URL_{project_name.upper()}"
        target_key_url_slug = f"DINGTALK_WEBHOOK_URL_{url_slug.upper()}" if url_slug else None

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
        raise ValueError(f"未找到项目 '{project_name}' 对应的钉钉Webhook URL，且未设置默认的 Webhook URL。")

    def send_message(self, content: str, msg_type='text', title='通知', is_at_all=False, project_name=None, url_slug=None, msg_category=None):
        if not self.enabled:
            logger.info("钉钉推送未启用")
            return

        try:
            post_url = self._get_webhook_url(project_name=project_name, url_slug=url_slug, msg_category=msg_category)
            headers = {
                "Content-Type": "application/json",
                "Charset": "UTF-8"
            }
            if msg_type == 'markdown':
                message = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": title,  # Customize as needed
                        "text": content
                    },
                    "at": {
                        "isAtAll": is_at_all
                    }
                }
            else:
                message = {
                    "msgtype": "text",
                    "text": {
                        "content": content
                    },
                    "at": {
                        "isAtAll": is_at_all
                    }
                }
            response = requests.post(url=post_url, data=json.dumps(message), headers=headers)
            response_data = response.json()
            if response_data.get('errmsg') == 'ok':
                logger.info(f"钉钉消息发送成功! webhook_url:{post_url}")
            else:
                logger.error(f"钉钉消息发送失败! webhook_url:{post_url},errmsg:{response_data.get('errmsg')}")
        except Exception as e:
            logger.error(f"钉钉消息发送失败! ", e)
