import json
import os
from typing import Dict, List, Optional
from biz.utils.log import logger


class UserMatcher:
    """用户匹配工具，用于匹配GitLab用户和飞书用户"""

    def __init__(self, feishu_user_file=None, gitlab_user_file=None):
        """
        初始化用户匹配器
        :param feishu_user_file: 飞书用户信息文件路径
        :param gitlab_user_file: GitLab用户信息文件路径
        """
        self.feishu_user_file = feishu_user_file or os.path.join(
            os.path.dirname(__file__), 'feishu-user.json'
        )
        self.gitlab_user_file = gitlab_user_file or os.path.join(
            os.path.dirname(__file__), 'gitlab-user.json'
        )

        self.feishu_users = self._load_feishu_users()
        self.gitlab_users = self._load_gitlab_users()

        # 创建匹配映射
        self.name_to_openid_map = self._create_name_mapping()

    def _load_feishu_users(self) -> List[Dict]:
        """加载飞书用户信息"""
        try:
            if not os.path.exists(self.feishu_user_file):
                logger.warning(f"飞书用户文件不存在: {self.feishu_user_file}")
                return []

            with open(self.feishu_user_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
                return users
        except Exception as e:
            logger.error(f"加载飞书用户文件失败: {str(e)}")
            return []

    def _load_gitlab_users(self) -> List[Dict]:
        """加载GitLab用户信息"""
        try:
            if not os.path.exists(self.gitlab_user_file):
                logger.warning(f"GitLab用户文件不存在: {self.gitlab_user_file}")
                return []

            with open(self.gitlab_user_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
                return users
        except Exception as e:
            logger.error(f"加载GitLab用户文件失败: {str(e)}")
            return []

    def _create_name_mapping(self) -> Dict[str, str]:
        """创建姓名到open_id的映射"""
        name_map = {}
        for user in self.feishu_users:
            name = user.get('name', '').strip()
            open_id = user.get('open_id', '')
            if name and open_id:
                name_map[name] = open_id

        return name_map

    def get_all_feishu_users(self) -> List[Dict]:
        """获取所有飞书用户信息"""
        return self.feishu_users

    def get_all_gitlab_users(self) -> List[Dict]:
        """获取所有GitLab用户信息"""
        return self.gitlab_users

    def get_user_mapping_stats(self) -> Dict:
        """获取用户映射统计信息"""
        return {
            'feishu_users_count': len(self.feishu_users),
            'gitlab_users_count': len(self.gitlab_users),
            'name_mappings_count': len(self.name_to_openid_map),
        }

    def get_openid_by_author(self, author: str) -> Optional[str]:
        """
        根据作者名称获取飞书open_id
        :param author: 作者名称
        :return: open_id或None
        """
        if not author:
            return None

        # 如果直接匹配失败，尝试通过GitLab用户信息匹配
        for user in self.gitlab_users:
            if user.get('name') == author or user.get('username') == author:
                # 找到GitLab用户后，通过显示名称获取open_id
                gitlab_name = user.get('name')
                if gitlab_name:
                    open_id = self.get_openid_by_name(gitlab_name)
                    if open_id:
                        return open_id

        logger.warning(f"无法匹配 gitlab 作者 {author} 的飞书open_id")
        return None

    def get_openid_by_name(self, name: str) -> Optional[str]:
        """
        根据姓名获取open_id
        :param name: 用户姓名
        :return: open_id或None
        """
        if not name:
            return None

        name = name.strip()
        open_id = self.name_to_openid_map.get(name)

        return open_id
