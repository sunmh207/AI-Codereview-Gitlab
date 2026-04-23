"""
OpenCode Serve API 客户端
负责与 opencode serve 后端通信，创建 session 并发送 review 请求
"""

import os
import time
from urllib.parse import urlparse

import requests

from biz.utils.log import logger


def _extract_title_from_url(mr_url: str) -> str:
    """
    从 MR/PR URL 中提取标题
    
    例如: https://github.com/linux/-/merge_requests/126
    返回: linux/-/merge_requests/126
    
    :param mr_url: Merge Request 或 Pull Request 的 URL
    :return: 提取的标题
    """
    try:
        parsed = urlparse(mr_url)
        path = parsed.path.strip('/')
        
        # 查找 /-/merge_requests/ 或 /-/pull/ 的位置
        mr_pattern = '/-/merge_requests/'
        pr_pattern = '/-/pull/'
        
        if mr_pattern in path:
            # GitLab MR URL
            parts = path.split(mr_pattern)
            if len(parts) == 2:
                project_path = parts[0]
                mr_number = parts[1]
                # 获取项目名（最后一个路径段）
                project_name = project_path.split('/')[-1]
                return f"{project_name}/-/merge_requests/{mr_number}"
        elif pr_pattern in path:
            # GitLab PR URL (如果存在)
            parts = path.split(pr_pattern)
            if len(parts) == 2:
                project_path = parts[0]
                pr_number = parts[1]
                project_name = project_path.split('/')[-1]
                return f"{project_name}/-/pull/{pr_number}"
        elif '/pull/' in path:
            # GitHub PR URL
            parts = path.split('/pull/')
            if len(parts) == 2:
                project_path = parts[0]
                pr_number = parts[1]
                project_name = project_path.split('/')[-1]
                return f"{project_name}/pull/{pr_number}"
        
        # 如果无法解析，返回默认标题
        logger.warning(f"[OpenCode] 无法从 URL 中提取标题: {mr_url}")
        return "Webhook Code Review"
    except Exception as e:
        logger.warning(f"[OpenCode] 解析 URL 标题时出错: {e}, URL: {mr_url}")
        return "Webhook Code Review"


def is_opencode_enabled() -> bool:
    """检查 OpenCode Review 是否启用"""
    return os.environ.get("OPENCODE_ENABLED", "0") == "1"


def _check_agent_exists(api_url: str, agent_name: str, auth=None) -> bool:
    """
    检查指定的 agent 是否存在
    
    :param api_url: OpenCode API URL
    :param agent_name: Agent 名称
    :param auth: 认证信息
    :return: True 如果 agent 存在，False 否则
    """
    try:
        agents_url = f"{api_url.rstrip('/')}/agent"
        logger.info(f"[OpenCode] 检查 agent 是否存在: GET {agents_url}")
        resp = requests.get(agents_url, auth=auth, timeout=10)
        resp.raise_for_status()
        agents = resp.json()
        
        agent_names = [agent.get("name") for agent in agents if isinstance(agent, dict)]
        exists = agent_name in agent_names
        
        if exists:
            logger.info(f"[OpenCode] Agent '{agent_name}' 存在")
        else:
            logger.warning(
                f"[OpenCode] Agent '{agent_name}' 不存在！可用 agents: {agent_names}"
            )
        return exists
    except Exception as e:
        logger.warning(f"[OpenCode] 无法检查 agent 是否存在: {e}")
        return True  # 如果检查失败，假设存在（向后兼容）


def send_opencode_review(mr_url: str):
    """
    向 opencode serve API 发送 review 请求。
    流程:
    1. 创建一个新的 session
    2. 向该 session 发送 review 消息（MR/PR URL 由 webhook 传入），指定 agent

    :param mr_url: 来自 webhook 的 Merge Request / Pull Request 链接
    """
    if not is_opencode_enabled():
        return

    api_url = os.environ.get("OPENCODE_API_URL", "http://localhost:4096")
    agent_name = os.environ.get("OPENCODE_AGENT_NAME", "code-reviewer")
    review_message = f"review this mr: {mr_url}"

    # 准备认证信息（如果配置了密码）
    auth = None
    server_password = os.environ.get("OPENCODE_SERVER_PASSWORD")
    server_username = os.environ.get("OPENCODE_SERVER_USERNAME", "opencode")
    if server_password:
        from requests.auth import HTTPBasicAuth
        auth = HTTPBasicAuth(server_username, server_password)

    try:
        # Step 1: 创建 session
        session_url = f"{api_url.rstrip('/')}/session"
        session_title = _extract_title_from_url(mr_url)
        logger.info(f"[OpenCode] 创建 session: POST {session_url}")
        create_resp = requests.post(
            session_url,
            json={"title": session_title},
            headers={"Content-Type": "application/json"},
            auth=auth,
            timeout=30,
        )
        create_resp.raise_for_status()
        session_data = create_resp.json()
        session_id = session_data.get("id")
        if not session_id:
            logger.error(f"[OpenCode] 创建 session 失败，响应中没有 id: {session_data}")
            return

        logger.info(f"[OpenCode] Session 创建成功: {session_id}")

        # Step 1.5: 验证 agent 是否存在（可选，用于调试）
        agent_exists = _check_agent_exists(api_url, agent_name, auth)
        if not agent_exists:
            logger.error(
                f"[OpenCode] Agent '{agent_name}' 不存在，请求可能会失败。"
                f"请检查 OPENCODE_AGENT_NAME 配置或创建相应的 agent。"
            )
            # 继续执行，让 API 返回明确的错误信息

        # Step 2: 发送 review 消息
        message_url = f"{api_url.rstrip('/')}/session/{session_id}/message"
        payload = {
            "agent": agent_name,
            "parts": [
                {
                    "type": "text",
                    "text": review_message,
                }
            ],
        }
        logger.info(
            f"[OpenCode] 准备发送 review 请求: POST {message_url}"
        )
        logger.info(
            f"[OpenCode] 请求参数: agent={agent_name}, payload={payload}"
        )

        # 使用较长的超时，因为 AI review 可能需要较长时间
        start_time = time.time()
        logger.info(f"[OpenCode] 开始发送请求，超时时间: 300秒")
        
        try:
            message_resp = requests.post(
                message_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                auth=auth,
                timeout=300,
            )
            elapsed_time = time.time() - start_time
            logger.info(
                f"[OpenCode] 请求完成，耗时: {elapsed_time:.2f}秒, 状态码: {message_resp.status_code}"
            )
            
            message_resp.raise_for_status()
            
            result = message_resp.json()
            logger.info(f"[OpenCode] Review 请求成功，响应: {result}")
            return result
        except requests.exceptions.Timeout:
            elapsed_time = time.time() - start_time
            logger.error(
                f"[OpenCode] 请求超时！耗时: {elapsed_time:.2f}秒 (超时设置: 300秒)"
            )
            logger.error(
                f"[OpenCode] 可能的原因: 1) agent '{agent_name}' 不存在或配置错误 "
                f"2) opencode serve 未正确处理请求 3) 网络连接问题"
            )
            raise

    except requests.exceptions.ConnectionError as e:
        logger.error(f"[OpenCode] 无法连接到 opencode serve ({api_url}): {e}")
        logger.error(f"[OpenCode] 请检查: 1) opencode serve 是否正在运行 2) API_URL 配置是否正确")
    except requests.exceptions.Timeout as e:
        logger.error(f"[OpenCode] 请求 opencode serve 超时: {e}")
        logger.error(
            f"[OpenCode] 调试建议: "
            f"1) 检查 agent '{agent_name}' 是否存在 (GET {api_url}/agent) "
            f"2) 查看 opencode serve 日志 "
            f"3) 检查 session 状态 (GET {api_url}/session/{session_id if 'session_id' in locals() else 'N/A'})"
        )
    except requests.exceptions.HTTPError as e:
        error_response = "N/A"
        if e.response is not None:
            try:
                error_response = e.response.text
            except:
                error_response = f"状态码: {e.response.status_code}"
        logger.error(
            f"[OpenCode] opencode serve 返回 HTTP 错误: {e}, 响应: {error_response}"
        )
        logger.error(
            f"[OpenCode] 请求 URL: {message_url if 'message_url' in locals() else 'N/A'}, "
            f"Payload: {payload if 'payload' in locals() else 'N/A'}"
        )
    except Exception as e:
        import traceback
        logger.error(f"[OpenCode] 发送 review 请求时出现未知错误: {e}")
        logger.error(f"[OpenCode] 错误堆栈: {traceback.format_exc()}")


if __name__ == "__main__":
    # 如果直接运行此文件，提示使用测试脚本
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from dotenv import load_dotenv
    env_file = project_root / "conf" / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    
    print("提示: 建议使用测试脚本运行测试:")
    print(f"  python biz/utils/test_opencode_client.py")
    print(f"  python biz/utils/test_opencode_client.py --manual")
    print()
    
    # 简单测试
    test_url = "https://github.com/sunmh207/AI-Codereview-Gitlab/pull/170"
    print(f"快速测试: {test_url}")
    send_opencode_review(test_url)