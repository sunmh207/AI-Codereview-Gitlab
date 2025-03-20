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
                raise ValueError(_("未提供项目名称，且未设置默认的企业微信 Webhook URL。"))

        # 遍历所有环境变量（忽略大小写），找到项目对应的 Webhook URL
        target_key = f"WECOM_WEBHOOK_URL_{project_name.upper()}"

        # 仓库名称优先级高，先匹配
        for env_key, env_value in os.environ.items():
            if env_key.upper() == target_key :
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

    def send_message(self, content, msg_type='text', title=None, is_at_all=False, project_name=None, url_base=None):
        """
        发送企业微信消息
        :param content: 消息内容
        :param msg_type: 消息类型，支持text和markdown
        :param title: 消息标题(markdown类型时使用)
        :param is_at_all: 是否@所有人
        """
        if not self.enabled:
            logger.info(_("企业微信推送未启用"))
            return

        try:
            post_url = self._get_webhook_url(project_name=project_name, url_base=url_base)
            if msg_type == 'markdown':
                formatted_content = self.format_markdown_content(content, title)
                data = {
                    "msgtype": "markdown",
                    "markdown": {
                        "content": formatted_content
                    }
                }
            else:
                data = {
                    "msgtype": "text",
                    "text": {
                        "content": content,
                        "mentioned_list": ["@all"] if is_at_all else []
                    }
                }

            response = requests.post(
                url=post_url,
                json=data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code != 200:
                logger.error(_("企业微信消息发送失败! webhook_url:{}, error_msg:{}").format(post_url, response.text))

                try:
                    data = json.loads(response.text)
                    errmsg = data.get("errmsg")
                    if errmsg and "markdown.content exceed max length" in errmsg:
                        # markdown渲染过长了，尝试text发送
                        data = {
                            "msgtype": "text",
                            "text": {
                                "content": content,
                                "mentioned_list": ["@all"] if is_at_all else []
                            }
                        }

                        response = requests.post(
                            url=post_url,
                            json=data,
                            headers={'Content-Type': 'application/json'}
                        )

                except json.JSONDecodeError as e:
                    print(f"JSON 解析失败: {e}")
                except Exception as e:
                    logger.error(_("企业微信消息发送失败! {}").format(e))
                return

            result = response.json()
            if result.get('errcode') != 0:
                logger.error(_("企业微信消息发送失败! webhook_url: {post_url}, errmsg: {result}").format(post_url=post_url, result=result))
            else:
                logger.info(_("企业微信消息发送成功! webhook_url: {}").format(post_url))

        except Exception as e:
            logger.error(_("企业微信消息发送失败!"), e)
