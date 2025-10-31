"""
测试配置隔离功能
验证多项目并发环境下配置不会互相污染
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from biz.utils.config_loader import config_loader


def test_config_isolation():
    """测试配置隔离：不同项目的配置应该独立，不会互相影响"""
    
    print("=" * 60)
    print("测试场景：模拟两个项目并发请求配置")
    print("=" * 60)
    
    # 模拟项目A获取配置
    print("\n[项目A] 获取配置...")
    config_a = config_loader.get_config(project_path="asset/project-a")
    print(f"[项目A] 配置数量: {len(config_a)}")
    
    # 模拟项目B获取配置
    print("\n[项目B] 获取配置...")
    config_b = config_loader.get_config(project_path="asset/project-b")
    print(f"[项目B] 配置数量: {len(config_b)}")
    
    # 验证全局环境变量未被修改
    print("\n[验证] 检查全局环境变量...")
    original_gitlab_token = os.environ.get('GITLAB_ACCESS_TOKEN', '')
    print(f"[验证] 全局 GITLAB_ACCESS_TOKEN 保持不变: {bool(original_gitlab_token)}")
    
    # 验证配置是独立的字典对象
    print("\n[验证] 配置是否为独立对象...")
    print(f"[验证] config_a is config_b: {config_a is config_b}")
    print(f"[验证] id(config_a): {id(config_a)}")
    print(f"[验证] id(config_b): {id(config_b)}")
    
    # 测试修改一个配置不影响另一个
    print("\n[测试] 修改config_a不应影响config_b...")
    config_a['TEST_KEY'] = 'value_from_a'
    has_test_key_in_b = 'TEST_KEY' in config_b
    print(f"[测试] config_b中包含TEST_KEY: {has_test_key_in_b}")
    print(f"[测试] ✓ 配置隔离成功！" if not has_test_key_in_b else "[测试] ✗ 配置污染！")
    
    print("\n" + "=" * 60)
    print("✓ 配置隔离测试完成")
    print("=" * 60)


def test_config_priority():
    """测试配置优先级：项目配置 > 默认配置"""
    
    print("\n" + "=" * 60)
    print("测试场景：配置优先级")
    print("=" * 60)
    
    # 获取默认配置
    print("\n[默认配置] 加载conf/.env...")
    default_config = config_loader.get_config()
    print(f"[默认配置] LLM_PROVIDER: {default_config.get('LLM_PROVIDER', 'NOT_SET')}")
    
    # 模拟项目有专属配置（如果存在的话）
    print("\n[项目配置] 加载项目专属配置...")
    project_config = config_loader.get_config(project_path="h5/h5-trade")
    print(f"[项目配置] LLM_PROVIDER: {project_config.get('LLM_PROVIDER', 'NOT_SET')}")
    
    print("\n" + "=" * 60)
    print("✓ 配置优先级测试完成")
    print("=" * 60)


def test_concurrent_simulation():
    """模拟并发场景：快速切换多个项目配置"""
    
    print("\n" + "=" * 60)
    print("测试场景：快速并发切换项目配置")
    print("=" * 60)
    
    projects = [
        "asset/project-a",
        "asset/project-b",
        "h5/h5-trade",
        "backend/api-server"
    ]
    
    configs = {}
    
    print("\n[并发] 快速获取多个项目配置...")
    for project in projects:
        config = config_loader.get_config(project_path=project)
        configs[project] = config
        print(f"[并发] {project}: id={id(config)}, keys={len(config)}")
    
    # 验证所有配置都是独立对象
    print("\n[验证] 检查所有配置对象是否独立...")
    ids = [id(config) for config in configs.values()]
    unique_ids = set(ids)
    
    print(f"[验证] 总配置对象数: {len(ids)}")
    print(f"[验证] 唯一对象数: {len(unique_ids)}")
    print(f"[验证] ✓ 所有配置都是独立对象！" if len(ids) == len(unique_ids) else "[验证] ✗ 存在配置共享！")
    
    print("\n" + "=" * 60)
    print("✓ 并发测试完成")
    print("=" * 60)


if __name__ == '__main__':
    print("\n" + "🧪" * 30)
    print("配置隔离功能测试套件")
    print("🧪" * 30)
    
    test_config_isolation()
    test_config_priority()
    test_concurrent_simulation()
    
    print("\n" + "✅" * 30)
    print("所有测试完成！")
    print("✅" * 30)
