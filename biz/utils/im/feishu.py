import requests
import os
import json
import time
from typing import List, Dict
from biz.utils.log import logger


class FeishuNotifier:
    def __init__(self, webhook_url=None):
        """
        初始化飞书通知器
        :param webhook_url: 飞书机器人webhook地址
        """
        self.default_webhook_url = webhook_url or os.environ.get('FEISHU_WEBHOOK_URL', '')
        self.enabled = os.environ.get('FEISHU_ENABLED', '0') == '1'

        # 飞书开放平台API配置
        self.app_id = os.environ.get('FEISHU_APP_ID', '')
        self.app_secret = os.environ.get('FEISHU_APP_SECRET', '')
        self.base_url = 'https://open.feishu.cn/open-apis'
        self._access_token = None
        self._token_expires_at = 0

    def _get_webhook_url(self, project_name=None, url_slug=None):
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
                raise ValueError("未提供项目名称，且未设置默认的 飞书 Webhook URL。")

        # 构造目标键
        target_key_project = f"FEISHU_WEBHOOK_URL_{project_name.upper()}"
        target_key_url_slug = f"FEISHU_WEBHOOK_URL_{url_slug.upper()}"

        # 遍历环境变量
        for env_key, env_value in os.environ.items():
            env_key_upper = env_key.upper()
            if env_key_upper == target_key_project:
                return env_value  # 找到项目名称对应的 Webhook URL，直接返回
            if env_key_upper == target_key_url_slug:
                return env_value  # 找到 GitLab URL 对应的 Webhook URL，直接返回

        # 如果未找到匹配的环境变量，降级使用全局的 Webhook URL
        if self.default_webhook_url:
            return self.default_webhook_url

        # 如果既未找到匹配项，也没有默认值，抛出异常
        raise ValueError(f"未找到项目 '{project_name}' 对应的 Feishu Webhook URL，且未设置默认的 Webhook URL。")

    def send_message(self, content, msg_type='text', title=None, is_at_all=False, project_name=None, url_slug=None):
        """
        发送飞书消息
        :param content: 消息内容
        :param msg_type: 消息类型，支持text和markdown
        :param title: 消息标题(markdown类型时使用)
        :param is_at_all: 是否@所有人
        :param project_name: 项目名称
        """
        if not self.enabled:
            logger.info("飞书推送未启用")
            return

        try:
            post_url = self._get_webhook_url(project_name=project_name, url_slug=url_slug)
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

    def send_direct_message(self, open_id, content, msg_type='text'):
        """
        直接发送消息给指定用户
        :param open_id: 用户的open_id
        :param content: 消息内容
        :param msg_type: 消息类型，支持text、rich_text等
        :return: 发送是否成功
        """
        if not self.enabled:
            logger.info("飞书推送未启用")
            return False

        if not open_id:
            logger.error("用户open_id不能为空")
            return False

        access_token = self._get_access_token()
        if not access_token:
            logger.error("无法获取飞书访问令牌")
            return False

        url = f"{self.base_url}/im/v1/messages?receive_id_type=open_id"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # 构造消息内容
        if msg_type == 'text':
            message_content = {
                "text": content
            }
        elif msg_type == 'rich_text':
            # 富文本消息格式
            message_content = content
        else:
            logger.error(f"不支持的消息类型: {msg_type}")
            return False

        payload = {
            "receive_id": open_id,
            "msg_type": msg_type,
            "content": json.dumps(message_content, ensure_ascii=False)
        }

        try:
            logger.debug(f"发送飞书消息请求: URL={url}, payload={payload}")
            response = requests.post(url, json=payload, headers=headers)

            # 获取响应内容
            try:
                result = response.json()
            except:
                result = {"error": "无法解析响应JSON", "response_text": response.text}

            logger.debug(f"飞书API响应: status_code={response.status_code}, result={result}")

            if response.status_code == 200 and result.get('code') == 0:
                logger.info(f"飞书消息发送成功! open_id: {open_id}")
                return True
            else:
                logger.error(f"发送飞书消息失败! open_id: {open_id}, status_code: {response.status_code}, error: {result}")
                return False

        except Exception as e:
            logger.error(f"发送飞书消息异常! open_id: {open_id}, error: {str(e)}")
            return False

    def _get_access_token(self):
        """
        获取飞书访问令牌
        """
        current_time = int(time.time())

        # 如果token还未过期，直接返回
        if self._access_token and current_time < self._token_expires_at:
            return self._access_token

        if not self.app_id or not self.app_secret:
            logger.error("飞书应用ID或应用密钥未配置")
            return None

        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
            response.raise_for_status()

            result = response.json()
            if result.get('code') == 0:
                self._access_token = result.get('tenant_access_token')
                # 设置过期时间（提前5分钟过期）
                expires_in = result.get('expire', 7200)
                self._token_expires_at = current_time + expires_in - 300
                logger.info("飞书访问令牌获取成功")
                return self._access_token
            else:
                logger.error(f"获取飞书访问令牌失败: {result}")
                return None

        except Exception as e:
            logger.error(f"获取飞书访问令牌异常: {str(e)}")
            return None
