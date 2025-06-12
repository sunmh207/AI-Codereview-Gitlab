import os
from biz.utils.log import logger
import requests


class ExtraWebhookNotifier:
    def __init__(self, webhook_url=None):
        """
        初始化ExtraWebhook通知器
        :param webhook_url: 自定义webhook地址
        """
        self.default_webhook_url = webhook_url or os.environ.get('EXTRA_WEBHOOK_URL', '')
        self.enabled = os.environ.get('EXTRA_WEBHOOK_ENABLED', '0') == '1'

    def send_message(self, system_data: dict, webhook_data: dict):
        """
        发送额外自定义webhook消息
        :param system_data: 系统消息内容
        :param webhook_data: github、gitlab的push event、merge event的原始数据
        """
        if not self.enabled:
            logger.info("ExtraWebhook推送未启用")
            return

        try:
            data = {
                "ai_codereview_data": system_data,
                "webhook_data": webhook_data
            }
            response = requests.post(
                url=self.default_webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code != 200:
                logger.error(f"ExtraWebhook消息发送失败! webhook_url:{self.default_webhook_url}, error_msg:{response.text}")
                return

        except Exception as e:
            logger.error(f"ExtraWebhook消息发送失败! ", e)