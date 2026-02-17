#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenCode 客户端测试脚本
用于测试 opencode_client.py 的功能
"""
import os
import sys
from pathlib import Path
from unittest import TestCase, main

# 添加项目根目录到 Python 路径（用于独立运行）
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent.resolve()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # 加载环境变量
    from dotenv import load_dotenv
    env_file = project_root / "conf" / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        print(f"Warning: {env_file} not found, using default values")

from biz.utils.opencode_client import (
    is_opencode_enabled,
    send_opencode_review,
    _check_agent_exists,
)


class TestOpenCodeClient(TestCase):
    """OpenCode 客户端测试类"""

    def setUp(self):
        """设置测试环境"""
        self.test_mr_url = (
            "https://github.com/sunmh207/AI-Codereview-Gitlab/pull/170"
        )
        self.api_url = os.environ.get("OPENCODE_API_URL", "http://localhost:4096")
        self.agent_name = os.environ.get("OPENCODE_AGENT_NAME", "code-reviewer")

    def test_is_opencode_enabled(self):
        """测试 OpenCode 是否启用"""
        enabled = is_opencode_enabled()
        self.assertIsInstance(enabled, bool)
        print(f"\n[测试] OpenCode 启用状态: {enabled}")

    def test_check_agent_exists(self):
        """测试检查 agent 是否存在"""
        if not is_opencode_enabled():
            self.skipTest("OpenCode 未启用，跳过测试")
        
        # 准备认证信息
        auth = None
        server_password = os.environ.get("OPENCODE_SERVER_PASSWORD")
        server_username = os.environ.get("OPENCODE_SERVER_USERNAME", "opencode")
        if server_password:
            from requests.auth import HTTPBasicAuth
            auth = HTTPBasicAuth(server_username, server_password)
        
        exists = _check_agent_exists(self.api_url, self.agent_name, auth)
        self.assertIsInstance(exists, bool)
        print(f"\n[测试] Agent '{self.agent_name}' 存在: {exists}")

    def test_send_opencode_review(self):
        """测试发送 OpenCode review 请求"""
        if not is_opencode_enabled():
            self.skipTest("OpenCode 未启用，跳过测试")
        
        print(f"\n[测试] 开始测试发送 review 请求...")
        print(f"[测试] MR URL: {self.test_mr_url}")
        print(f"[测试] API URL: {self.api_url}")
        print(f"[测试] Agent: {self.agent_name}")
        print("-" * 60)
        
        try:
            result = send_opencode_review(self.test_mr_url)
            if result:
                print(f"\n[测试] ✓ Review 请求成功，返回结果: {result}")
                self.assertIsNotNone(result)
            else:
                print(f"\n[测试] ⚠ Review 函数返回 None（可能被禁用或失败）")
        except Exception as e:
            print(f"\n[测试] ✗ 发生错误: {e}")
            import traceback
            traceback.print_exc()
            # 不抛出异常，让测试继续，这样可以看到完整的错误信息
            self.fail(f"发送 review 请求失败: {e}")


def run_manual_test():
    """手动测试函数（用于快速测试）"""
    print("=" * 60)
    print("OpenCode 客户端手动测试")
    print("=" * 60)
    
    # 检查是否启用
    enabled = is_opencode_enabled()
    print(f"\n1. OpenCode 启用状态: {enabled}")
    
    if not enabled:
        print("\n⚠ OpenCode 未启用，请设置 OPENCODE_ENABLED=1")
        return
    
    # 检查 agent
    api_url = os.environ.get("OPENCODE_API_URL", "http://localhost:4096")
    agent_name = os.environ.get("OPENCODE_AGENT_NAME", "code-reviewer")
    
    print(f"\n2. API URL: {api_url}")
    print(f"3. Agent Name: {agent_name}")
    
    # 准备认证信息
    auth = None
    server_password = os.environ.get("OPENCODE_SERVER_PASSWORD")
    server_username = os.environ.get("OPENCODE_SERVER_USERNAME", "opencode")
    if server_password:
        from requests.auth import HTTPBasicAuth
        auth = HTTPBasicAuth(server_username, server_password)
        print(f"4. 认证: 已配置 (username: {server_username})")
    else:
        print("4. 认证: 未配置")
    
    # 检查 agent
    print(f"\n5. 检查 agent '{agent_name}' 是否存在...")
    try:
        exists = _check_agent_exists(api_url, agent_name, auth)
        print(f"   Agent 存在: {exists}")
    except Exception as e:
        print(f"   ⚠ 检查 agent 时出错: {e}")
    
    # 发送测试请求
    test_url = "https://github.com/sunmh207/AI-Codereview-Gitlab/pull/170"
    print(f"\n6. 发送 review 请求...")
    print(f"   URL: {test_url}")
    print("-" * 60)
    
    try:
        result = send_opencode_review(test_url)
        if result:
            print("\n✓ Review 请求成功完成")
            print(f"结果: {result}")
        else:
            print("\n⚠ Review 函数返回 None")
    except Exception as e:
        print(f"\n✗ Review 请求失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试 OpenCode 客户端")
    parser.add_argument(
        "--manual",
        action="store_true",
        help="运行手动测试（更详细的输出）",
    )
    args = parser.parse_args()
    
    if args.manual:
        run_manual_test()
    else:
        # 运行 unittest 测试
        main(verbosity=2)
