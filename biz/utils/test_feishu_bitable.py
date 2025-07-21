#!/usr/bin/env python3
"""
飞书多维表格连接测试脚本
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("../../conf/.env")

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from biz.utils.feishu_bitable import FeishuBitableClient
from biz.entity.review_entity import PushReviewEntity
from datetime import datetime


def test_feishu_bitable_connection():
    """测试飞书多维表格连接"""
    print("=== 飞书多维表格连接测试 ===")

    client = FeishuBitableClient()

    # 检查配置
    print(f"飞书多维表格功能启用状态: {client.enabled}")
    print(f"应用ID: {client.app_id[:10]}..." if client.app_id else "应用ID: 未配置")
    print(f"应用密钥: {'已配置' if client.app_secret else '未配置'}")
    print(f"表格应用Token: {client.app_token[:10]}..." if client.app_token else "表格应用Token: 未配置")
    print(f"表格ID: {client.table_id[:10]}..." if client.table_id else "表格ID: 未配置")

    if not client.enabled:
        print("❌ 飞书多维表格功能未启用，请在.env文件中设置 FEISHU_BITABLE_ENABLED=1")
        return False

    # 测试连接
    print("\n正在测试连接...")
    if client.test_connection():
        print("✅ 飞书多维表格连接测试成功！")
        return True
    else:
        print("❌ 飞书多维表格连接测试失败！")
        return False


def test_create_record():
    """测试创建记录"""
    print("\n=== 测试创建记录 ===")

    client = FeishuBitableClient()

    if not client.enabled:
        print("❌ 飞书多维表格功能未启用")
        return False

    # 创建测试用的PushReviewEntity
    test_entity = PushReviewEntity(
        project_name="测试项目",
        author="测试开发者",
        branch="main",
        updated_at=int(datetime.now().timestamp()),
        commits=[
            {"id": "commitId1", "url": "https://test.com/commit/commitId1", "message": "测试提交1", "author": "测试开发者", "timestamp": "2025-01-18 10:00:00"},
            {"id": "commitId2","url": "https://test.com/commit/commitId2", "message": "测试提交2", "author": "测试开发者", "timestamp": "2025-01-18 10:30:00"}
        ],
        score=85.5,
        review_result="代码质量良好，建议优化性能部分。",
        url_slug="test_project",
        webhook_data={},
        additions=50,
        deletions=10
    )

    print("正在创建测试记录...")
    if client.create_push_review_record(test_entity):
        print("✅ 测试记录创建成功！")
        return True
    else:
        print("❌ 测试记录创建失败！")
        return False


def main():
    """主函数"""
    print("飞书多维表格集成测试")
    print("=" * 50)

    # 测试连接
    connection_ok = test_feishu_bitable_connection()

    if connection_ok:
        # 测试创建记录
        create_ok = test_create_record()

        if create_ok:
            print("\n🎉 所有测试通过！飞书多维表格集成配置正确。")
        else:
            print("\n⚠️  连接正常但创建记录失败，请检查表格字段配置。")
    else:
        print("\n❌ 连接测试失败，请检查配置。")
        print("\n配置说明：")
        print("1. 在.env文件中设置以下配置项：")
        print("   FEISHU_BITABLE_ENABLED=1")
        print("   FEISHU_APP_ID=你的应用ID")
        print("   FEISHU_APP_SECRET=你的应用密钥")
        print("   FEISHU_BITABLE_APP_TOKEN=你的多维表格应用Token")
        print("   FEISHU_BITABLE_TABLE_ID=你的表格ID")
        print("\n2. 确保飞书应用有多维表格的读写权限")
        print("3. 确保多维表格中有对应的字段")


if __name__ == "__main__":
    main()
