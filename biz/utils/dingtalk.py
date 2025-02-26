import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse

import requests
from dotenv import load_dotenv

from biz.utils.log import logger


class DingTalkNotifier:
    def __init__(self, webhook_url=None, project_name=None):
        self.enabled = os.environ.get('DINGTALK_ENABLED', '0') == '1'
        #打印项目名称
        logger.info(f"项目名称:{project_name}")
        #打印os.environ.get(f'DINGTALK_WEBHOOK_URL_{project_name}', '')
        #打印os.environ.get('DINGTALK_WEBHOOK_URL', '')
        logger.info(f"钉钉webhook:{webhook_url}")

        if project_name:
            self.webhook_url = webhook_url or os.environ.get(f'DINGTALK_WEBHOOK_URL_{project_name}', '') or os.environ.get('DINGTALK_WEBHOOK_URL', '')
        else:
            self.webhook_url = webhook_url or os.environ.get('DINGTALK_WEBHOOK_URL', '')
        self.secret = os.environ.get('DINGTALK_SECRET', None)

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
