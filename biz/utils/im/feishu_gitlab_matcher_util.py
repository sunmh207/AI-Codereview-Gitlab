#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户匹配脚本
注意：使用前先导入 feishu-user.json 和 gitlab-user.json 文件

select name, open_id, gitlab-user.username as gitlab_username
from feishu-user
left join gitlab-user on feishu-user.name = gitlab-user.name
"""

import json
import os
from typing import List, Dict, Optional


def load_json_file(file_path: str) -> List[Dict]:
    """
    加载JSON文件

    Args:
        file_path: JSON文件路径

    Returns:
        解析后的JSON数据列表

    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON格式错误
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"JSON格式错误 {file_path}: {e}")


def create_gitlab_user_map(gitlab_users: List[Dict]) -> Dict[str, str]:
    """
    创建GitLab用户名映射表

    Args:
        gitlab_users: GitLab用户列表

    Returns:
        以name为key，username为value的映射字典
    """
    user_map = {}
    for user in gitlab_users:
        name = user.get('name', '').strip()
        username = user.get('username', '').strip()
        if name and username:
            user_map[name] = username
    return user_map


def match_users(feishu_users: List[Dict], gitlab_user_map: Dict[str, str]) -> List[Dict]:
    """
    匹配用户信息

    Args:
        feishu_users: 飞书用户列表
        gitlab_user_map: GitLab用户名映射表

    Returns:
        匹配结果列表，包含name、open_id、gitlab_username字段
    """
    matched_users = []
    unmatched_users = []

    for feishu_user in feishu_users:
        name = feishu_user.get('name', '').strip()
        open_id = feishu_user.get('open_id', '').strip()

        if not name or not open_id:
            continue

        # 查找匹配的GitLab用户名
        gitlab_username = gitlab_user_map.get(name)

        result = {
            'name': name,
            'open_id': open_id,
            'gitlab_username': gitlab_username
        }

        if gitlab_username:
            matched_users.append(result)
        else:
            unmatched_users.append(result)

    return matched_users, unmatched_users


def save_results(matched_users: List[Dict], unmatched_users: List[Dict], output_dir: str = None):
    """
    保存匹配结果

    Args:
        matched_users: 匹配成功的用户列表
        unmatched_users: 未匹配的用户列表
        output_dir: 输出目录，默认为当前脚本所在目录
    """
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))

    # 保存匹配成功的用户
    matched_file = os.path.join(output_dir, 'developer.json')
    with open(matched_file, 'w', encoding='utf-8') as f:
        json.dump(matched_users, f, ensure_ascii=False, indent=2)

    # 保存未匹配的用户
    unmatched_file = os.path.join(output_dir, 'unmatched_users.json')
    with open(unmatched_file, 'w', encoding='utf-8') as f:
        json.dump(unmatched_users, f, ensure_ascii=False, indent=2)

    return matched_file, unmatched_file


def main():
    """
    主函数
    """
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # JSON文件路径
    gitlab_file = os.path.join(script_dir, 'gitlab-user.json')
    feishu_file = os.path.join(script_dir, 'feishu-user.json')

    try:
        # 加载JSON文件
        gitlab_users = load_json_file(gitlab_file)
        feishu_users = load_json_file(feishu_file)

        # 创建GitLab用户映射表
        gitlab_user_map = create_gitlab_user_map(gitlab_users)
        print(f"GitLab用户映射表大小: {len(gitlab_user_map)}")

        # 匹配用户
        print("正在匹配用户...")
        matched_users, unmatched_users = match_users(feishu_users, gitlab_user_map)

        # 输出统计信息
        print(f"飞书用户总数: {len(feishu_users)}")
        print(f"匹配成功用户数: {len(matched_users)}")
        print(f"未匹配用户数: {len(unmatched_users)}")

        # 输出未匹配的用户信息
        if unmatched_users:
            print("\n未匹配到GitLab用户的飞书用户:")
            for user in unmatched_users:
                print(f"  - {user['name']} (open_id: {user['open_id']})")

        # 保存结果
        print("\n正在保存结果...")
        matched_file, unmatched_file = save_results(matched_users, unmatched_users)
        print(f"匹配成功用户已保存到: {matched_file}")
        print(f"未匹配用户已保存到: {unmatched_file}")

    except Exception as e:
        print(f"错误: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
