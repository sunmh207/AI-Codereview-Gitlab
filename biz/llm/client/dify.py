import os
import json
from typing import Dict, List, Optional
import requests

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.log import logger


class DifyClient(BaseClient):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DIFY_API_KEY")
        self.base_url = os.getenv("DIFY_API_BASE_URL", "https://api.dify.ai/v1")
        if not self.api_key:
            raise ValueError("DIFY_API_KEY is required. Please provide it or set it in the environment variables.")
        
        # 确保 base_url 以 /v1 结尾（Dify API 要求）
        if not self.base_url.endswith('/v1'):
            # 如果 base_url 已经包含路径，我们追加 /v1
            if self.base_url.endswith('/'):
                self.base_url = self.base_url.rstrip('/') + '/v1'
            else:
                self.base_url = self.base_url + '/v1'
        
        self.default_model = os.getenv("DIFY_API_MODEL", "gpt-3.5-turbo")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        try:
            # Dify API 不使用 model 参数，但为了接口兼容性保留
            model = model or self.default_model
            logger.debug(f"Sending request to Dify API. Base URL: {self.base_url}, Messages: {messages}")
            
            # 将 messages 转换为 Dify API 所需的格式
            # 查找最后一个用户消息作为 query
            query = ""
            user_messages = [msg for msg in messages if msg.get("role") == "user"]
            if user_messages:
                query = user_messages[-1].get("content", "")
            
            if not query:
                # 如果没有用户消息，尝试使用最后一个消息
                if messages:
                    query = messages[-1].get("content", "")
            
            if not query:
                logger.error("No query content found in messages")
                return "错误：消息中没有找到查询内容"
            
            # 构建 Dify API 请求体
            payload = {
                "query": query,
                "inputs": {},
                "response_mode": "blocking",  # 使用阻塞模式，等待完整响应
                "user": "ai-codereview-system",  # 固定用户标识
                "auto_generate_name": False
            }
            
            # 如果有系统消息，可以将其作为 inputs 的一部分传递
            system_messages = [msg for msg in messages if msg.get("role") == "system"]
            if system_messages:
                # 将系统消息内容作为输入变量传递
                system_content = system_messages[-1].get("content", "")
                if system_content:
                    payload["inputs"]["system_prompt"] = system_content
            
            logger.debug(f"Dify API payload: {payload}")
            
            # 发送请求到 Dify API
            response = requests.post(
                f"{self.base_url}/chat-messages",
                headers=self.headers,
                json=payload,
                timeout=300  # 5分钟超时
            )
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"Dify API 返回错误: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                if response.status_code == 401:
                    return "Dify API认证失败，请检查API密钥是否正确"
                elif response.status_code == 404:
                    return "Dify API接口未找到，请检查API地址是否正确"
                elif response.status_code == 400:
                    # 尝试解析错误信息
                    try:
                        error_data = response.json()
                        return f"Dify API请求参数错误: {error_data.get('message', '未知错误')}"
                    except:
                        return f"Dify API请求参数错误: {response.text}"
                else:
                    return f"调用Dify API时出错: {response.status_code} - {response.text}"
            
            # 解析响应
            response_data = response.json()
            
            # 检查响应格式
            if "answer" not in response_data:
                logger.error(f"Unexpected Dify API response format: {response_data}")
                return "AI服务返回格式异常，请稍后重试"
            
            answer = response_data.get("answer", "")
            
            if not answer:
                logger.error("Empty answer from Dify API")
                return "AI服务返回为空，请稍后重试"
                
            return answer
            
        except requests.exceptions.Timeout:
            logger.error("Dify API request timeout")
            return "Dify API请求超时，请稍后重试"
        except requests.exceptions.ConnectionError:
            logger.error("Dify API connection error")
            return "无法连接到Dify API，请检查网络连接和API地址"
        except Exception as e:
            logger.error(f"Dify API error: {str(e)}")
            return f"调用Dify API时出错: {str(e)}"
