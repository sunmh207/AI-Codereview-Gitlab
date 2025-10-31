import json
import requests
import os
import re
from biz.utils.log import logger


class WeComNotifier:
    def __init__(self, webhook_url=None):
        """
        初始化企业微信通知器
        :param webhook_url: 企业微信机器人webhook地址
        """
        self.default_webhook_url = webhook_url or os.environ.get('WECOM_WEBHOOK_URL', '')
        self.enabled = os.environ.get('WECOM_ENABLED', '0') == '1'

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
            category_webhook_key = f"WECOM_WEBHOOK_URL_{msg_category.upper()}"
            category_webhook_url = os.environ.get(category_webhook_key)
            if category_webhook_url:
                return category_webhook_url
            # 如果没有配置专用webhook，降级使用默认webhook
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError(f"未设置消息类别 '{msg_category}' 的专用 Webhook URL，且未设置默认的企业微信 Webhook URL。")
        
        # 如果未提供 project_name，直接返回默认的 Webhook URL
        if not project_name:
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError("未提供项目名称，且未设置默认的企业微信 Webhook URL。")

        # 构造目标键
        target_key_project = f"WECOM_WEBHOOK_URL_{project_name.upper()}"
        target_key_url_slug = f"WECOM_WEBHOOK_URL_{url_slug.upper()}" if url_slug else None

        # 遍历环境变量
        for env_key, env_value in os.environ.items():
            env_key_upper = env_key.upper()
            if env_key_upper == target_key_project:
                return env_value  # 找到项目名称对应的 Webhook URL，直接返回
            if target_key_url_slug and env_key_upper == target_key_url_slug:
                return env_value  # 找到 GitLab URL 对应的 Webhook URL，直接返回

        # 如果未找到匹配的环境变量，降级使用全局的 Webhook URL
        if self.default_webhook_url:
            return self.default_webhook_url

        # 如果既未找到匹配项，也没有默认值，抛出异常
        raise ValueError(f"未找到项目 '{project_name}' 对应的企业微信 Webhook URL，且未设置默认的 Webhook URL。")

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
                     url_slug=None, mentioned_list=None, msg_category=None):
        """
        发送企业微信消息
        :param content: 消息内容
        :param msg_type: 消息类型，支持 text 和 markdown
        :param title: 消息标题 (markdown 类型时使用)
        :param is_at_all: 是否 @所有人
        :param project_name: 关联项目名称
        :param url_slug: GitLab URL Slug
        :param mentioned_list: @指定用户列表，优先于is_at_all（仅text类型支持）
        :param msg_category: 消息类别（如：daily_report），用于区分不同场景的webhook
        """
        if not self.enabled:
            logger.info("企业微信推送未启用")
            return

        try:
            post_url = self._get_webhook_url(project_name=project_name, url_slug=url_slug, msg_category=msg_category)
            # 企业微信消息内容最大长度限制
            # text类型最大2048字节
            # https://developer.work.weixin.qq.com/document/path/91770#%E6%96%87%E6%9C%AC%E7%B1%BB%E5%9E%8B
            # markdown类型最大4096字节
            # https://developer.work.weixin.qq.com/document/path/91770#markdown%E7%B1%BB%E5%9E%8B
            MAX_CONTENT_BYTES = 4096 if msg_type == 'markdown' else 2048

            # 对于 markdown 类型，需要计算格式化后的实际长度（包括标题）
            if msg_type == 'markdown':
                # 模拟格式化后的内容，计算实际字节数
                formatted_content = self.format_markdown_content(content, title)
                if mentioned_list:
                    mention_tags = ' '.join([f'<@{user}>' for user in (mentioned_list if isinstance(mentioned_list, list) else [mentioned_list])])
                    formatted_content = f"{formatted_content}\n\n{mention_tags}"
                content_length = len(formatted_content.encode('utf-8'))
            else:
                # text 类型直接检查原始内容长度
                content_length = len(content.encode('utf-8'))
                # text 类型如果有 mentioned_list，也需要加上 mention_tags 的长度
                if mentioned_list:
                    mention_tags = ' '.join([f'<@{user}>' for user in (mentioned_list if isinstance(mentioned_list, list) else [mentioned_list])])
                    content_length += len(f"\n\n{mention_tags}".encode('utf-8'))

            if content_length <= MAX_CONTENT_BYTES:
                # 内容长度在限制范围内，直接发送
                data = self._build_message(content, title, msg_type, is_at_all, mentioned_list)
                self._send_message(post_url, data)
            else:
                # 内容超过限制，需要分割发送
                logger.warning(f"消息内容超过{MAX_CONTENT_BYTES}字节限制，将分割发送。总长度: {content_length}字节")
                self._send_message_in_chunks(content, title, post_url, msg_type, is_at_all, MAX_CONTENT_BYTES, mentioned_list)

        except Exception as e:
            logger.error(f"企业微信消息发送失败! {e}")

    def _send_message_in_chunks(self, content, title, post_url, msg_type, is_at_all, max_bytes, mentioned_list=None):
        """
        将内容分割成多个部分并分别发送
        """
        # 对于 markdown 类型，需要预留空间给标题和 mention_tags
        if msg_type == 'markdown':
            # 计算标题的开销（模拟格式："## {title} (第X/Y部分)\n\n"）
            # 使用最长的标题来计算（假设最多99个分块）
            sample_title = f"## {title} (第99/99部分)\n\n" if title else ""
            title_overhead = len(sample_title.encode('utf-8'))
            
            # 计算 mention_tags 的开销
            mention_overhead = 0
            if mentioned_list:
                mention_tags = ' '.join([f'<@{user}>' for user in (mentioned_list if isinstance(mentioned_list, list) else [mentioned_list])])
                mention_overhead = len(f"\n\n{mention_tags}".encode('utf-8'))
            
            # 实际可用的内容空间
            available_bytes = max_bytes - title_overhead - mention_overhead
        else:
            available_bytes = max_bytes
            # text 类型也需要考虑 mention_tags
            if mentioned_list:
                mention_tags = ' '.join([f'<@{user}>' for user in (mentioned_list if isinstance(mentioned_list, list) else [mentioned_list])])
                mention_overhead = len(f"\n\n{mention_tags}".encode('utf-8'))
                available_bytes -= mention_overhead
        
        chunks = self._split_content(content, available_bytes)
        for i, chunk in enumerate(chunks):
            chunk_title = f"{title} (第{i + 1}/{len(chunks)}部分)" if title else f"消息 (第{i + 1}/{len(chunks)}部分)"
            data = self._build_message(chunk, chunk_title, msg_type, is_at_all, mentioned_list)
            self._send_message(post_url, data, chunk_num=i + 1, total_chunks=len(chunks))

    def _split_content(self, content, max_bytes):
        """
        将内容按最大字节长度分割成多个部分
        """
        chunks = []
        start_pos = 0
        content_bytes = content.encode('utf-8')
        content_length = len(content_bytes)

        while start_pos < content_length:
            end_pos = start_pos + max_bytes
            if end_pos >= content_length:
                chunk = content_bytes[start_pos:].decode('utf-8', errors='ignore')
                chunks.append(chunk)
                break

            while end_pos > start_pos:
                if content_bytes[end_pos - 1:end_pos] == b'\n':
                    break
                end_pos -= 1

            chunk = content_bytes[start_pos:end_pos].decode('utf-8', errors='ignore')
            chunks.append(chunk)
            start_pos = end_pos

        return chunks

    def _send_message(self, post_url, data, chunk_num=None, total_chunks=None):
        """ 发送请求并返回响应 """
        try:
            logger.debug(
                f"发送企业微信消息{'分块' if chunk_num else ''} {chunk_num}/{total_chunks if chunk_num else ''}: url={post_url}, data={data}")
            response = self._send_request(post_url, data)

            if response and response.get('errcode') != 0:
                logger.error(f"企业微信消息发送失败! webhook_url:{post_url}, errmsg:{response}")
            else:
                logger.info(f"企业微信消息{'分块' if chunk_num else ''}发送成功! webhook_url:{post_url}")

        except Exception as e:
            logger.error(f"企业微信消息{'分块' if chunk_num else ''}发送失败! {e}")

    def _send_request(self, url, data):
        """ 发送请求并返回 JSON 响应 """
        try:
            response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
            response.raise_for_status()  # 触发 HTTP 错误
            return response.json()
        except requests.RequestException as e:
            logger.error(f"企业微信消息发送请求失败! url:{url}, error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"企业微信返回的 JSON 解析失败! url:{url}, error: {e}")
        return None

    def _build_message(self, content, title, msg_type, is_at_all, mentioned_list=None):
        """ 构造消息 """
        if msg_type == 'text':
            return self._build_text_message(content, is_at_all, mentioned_list)
        elif msg_type =='markdown':
            return self._build_markdown_message(content, title, mentioned_list)
        else:
            raise ValueError(f"不支持的消息类型: {msg_type}")

    def _build_text_message(self, content, is_at_all, mentioned_list=None):
        """ 构造纯文本消息 """
        # 如果提供了明确的mentioned_list，使用它；否则根据is_at_all决定
        if mentioned_list is not None:
            mentions = mentioned_list if isinstance(mentioned_list, list) else [mentioned_list]
        else:
            mentions = ["@all"] if is_at_all else []
        
        # 如果有mentioned_list，在content末尾添加<@userid>语法
        if mentioned_list:
            mention_tags = ' '.join([f'<@{user}>' for user in (mentioned_list if isinstance(mentioned_list, list) else [mentioned_list])])
            content = f"{content}\n\n{mention_tags}"
        
        return {
            "msgtype": "text",
            "text": {
                "content": content,
                "mentioned_list": mentions
            }
        }

    def _build_markdown_message(self, content, title, mentioned_list=None):
        """ 构造 Markdown 消息 """
        formatted_content = self.format_markdown_content(content, title)
        
        # 如果有mentioned_list，在content末尾添加<@userid>语法
        if mentioned_list:
            mention_tags = ' '.join([f'<@{user}>' for user in (mentioned_list if isinstance(mentioned_list, list) else [mentioned_list])])
            formatted_content = f"{formatted_content}\n\n{mention_tags}"
        
        return {
            "msgtype": "markdown",
            "markdown": {
                "content": formatted_content
            }
        }
