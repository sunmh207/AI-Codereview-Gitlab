import json
import requests
import os
import re
from biz.utils.log import logger
from biz.utils.i18n import get_translator
_ = get_translator()

class WeComNotifier:
    def __init__(self, webhook_url=None):
        """
        初始化企业微信通知器
        :param webhook_url: 企业微信机器人webhook地址
        """
        self.default_webhook_url = webhook_url or os.environ.get('WECOM_WEBHOOK_URL', '')
        self.enabled = os.environ.get('WECOM_ENABLED', '0') == '1'

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
                raise ValueError(_("未提供项目名称，且未设置默认的企业微信 Webhook URL。"))

        # 构造目标键
        target_key_project = f"WECOM_WEBHOOK_URL_{project_name.upper()}"
        target_key_url_slug = f"WECOM_WEBHOOK_URL_{url_slug.upper()}"

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
        raise ValueError(_("未找到项目 '{}' 对应的企业微信 Webhook URL，且未设置默认的 Webhook URL。").format(project_name))

    def format_markdown_content(self, content, title=None):
        """
        格式化markdown内容以适配企业微信
        """
        # 处理标题
        formatted_content = f"## {title}\n\n" if title else ""

        # 将内容中的5级以上标题转为4级
        content = re.sub(r'#{5,}\s', '#### ', content)

        # 处理链接格式
        content = re.sub(r'\[(.*?)\]\((.*?)\)', r'[链接]\2', content)

        # 移除HTML标签
        content = re.sub(r'<[^>]+>', '', content)

        formatted_content += content
        return formatted_content

    def send_message(self, content, msg_type='text', title=None, is_at_all=False, project_name=None,
                     url_slug=None):
        """
        发送企业微信消息
        :param content: 消息内容
        :param msg_type: 消息类型，支持 text 和 markdown
        :param title: 消息标题 (markdown 类型时使用)
        :param is_at_all: 是否 @所有人
        :param project_name: 关联项目名称
        :param url_slug: GitLab URL Slug
        """
        if not self.enabled:
            logger.info(_("企业微信推送未启用"))
            return

        try:
            post_url = self._get_webhook_url(project_name=project_name, url_slug=url_slug)
            data = self._build_markdown_message(content, title) if msg_type == 'markdown' else self._build_text_message(
                content, is_at_all)

            logger.debug(_("发送企业微信消息: url={post_url}, data={data}").format(post_url=post_url, data=data))
            response = self._send_request(post_url, data)

            if response and response.get('errcode') != 0:
                logger.error(_("企业微信消息发送失败! webhook_url:{}, error_msg:{}").format(post_url, response.text))
                if response.get("errmsg") and "markdown.content exceed max length" in response["errmsg"]:
                    logger.warning(_("Markdown 消息过长，尝试发送纯文本"))
                    data = self._build_text_message(content, is_at_all)
                    self._send_request(post_url, data)
            else:
                logger.info(_("企业微信消息发送成功! webhook_url: {}").format(post_url))

        except Exception as e:
            logger.error(_("企业微信消息发送失败!"), e)

    def _send_request(self, url, data):
        """ 发送请求并返回 JSON 响应 """
        try:
            response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
            response.raise_for_status()  # 触发 HTTP 错误
            return response.json()
        except requests.RequestException as e:
            logger.error(_("企业微信消息发送请求失败! url:{url}, error: {e}").format(url=url, e=e))
        except json.JSONDecodeError as e:
            logger.error(_("企业微信返回的 JSON 解析失败! url:{url}, error: {e}").format(url=url, e=e))
        return None

    def _build_text_message(self, content, is_at_all):
        """ 构造纯文本消息 """
        return {
            "msgtype": "text",
            "text": {
                "content": content,
                "mentioned_list": ["@all"] if is_at_all else []
            }
        }

    def _build_markdown_message(self, content, title):
        """ 构造 Markdown 消息 """
        formatted_content = self.format_markdown_content(content, title)
        return {
            "msgtype": "markdown",
            "markdown": {
                "content": formatted_content
            }
        }
