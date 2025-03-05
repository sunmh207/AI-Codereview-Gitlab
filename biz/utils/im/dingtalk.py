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
    def __init__(self, git_project_name=None):
        self.enabled = os.environ.get('DINGTALK_ENABLED', '0') == '1'
        self.webhook_url = self._get_webhook_url()
        self._git_project_name = git_project_name
        self.secret = self._get_project_secret()

    def _get_webhook_url(self):
        token = os.environ.get('DINGTALK_WEBHOOK_TOKEN', None)
        if self._git_project_name:
            token = os.environ.get(f"{self._git_project_name.upper()}_DINGTALK_WEBHOOK_TOKEN")

        if not token:
            raise ValueError("Webhook token not found. Please ensure 'DINGTALK_WEBHOOK_TOKEN' or "
                             f"{self._git_project_name.upper()}_DINGTALK_WEBHOOK_TOKEN is set in environment variables.")

        return f"https://oapi.dingtalk.com/robot/send?access_token={str(token)}"

    def _get_project_secret(self):
        env_key = f"{self._git_project_name.upper()}_DINGTALK_SECRET" if self._git_project_name else "DINGTALK_SECRET"
        return os.environ.get(env_key, None)

    def _generate_signature(self):
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{self.secret}'
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode('utf-8'))
        return timestamp, sign

    def _get_post_url(self):
        if not self.secret:
            return self.webhook_url
        timestamp, sign = self._generate_signature()
        return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"

    def send_message(self, content: str, msg_type='text', title='通知', is_at_all=False):
        if not self.enabled:
            logger.info("钉钉推送未启用")
            return

        if not self.webhook_url:
            logger.error("钉钉Webhook URL未配置")
            return
        try:
            logger.info(f"钉钉Webhook: {str(self.webhook_url)}")
            post_url = self._get_post_url()
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
                logger.info("钉钉消息发送成功!")
            else:
                logger.error(f"发送失败:{response_data.get('errmsg')}")
        except Exception as e:
            logger.error("发送钉钉消息失败:", e)
