import json
import os
from typing import Dict, List, Optional
from biz.utils.log import logger


class UserMatcher:
    def __init__(self, feishu_user_file=None, gitlab_user_file=None, developer_file=None):
        """
        初始化用户匹配器
        :param developer_file: 开发者映射文件路径
        """
        self.developer_file = developer_file or os.path.join(
            os.path.dirname(__file__), 'developer.json'
        )

        self.developers = self._load_developers()
        self.gitlab_username_to_openid_map = self._create_gitlab_username_mapping()

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

    def _load_developers(self) -> List[Dict]:
        """加载开发者映射信息"""
        try:
            if not os.path.exists(self.developer_file):
                logger.warning(f"开发者映射文件不存在: {self.developer_file}")
                return []

            with open(self.developer_file, 'r', encoding='utf-8') as f:
                developers = json.load(f)
                return developers
        except Exception as e:
            logger.error(f"加载开发者映射文件失败: {str(e)}")
            return []

    def _create_gitlab_username_mapping(self) -> Dict[str, str]:
        """创建GitLab用户名到open_id的映射"""
        username_map = {}
        for dev in self.developers:
            gitlab_username = dev.get('gitlab_username', '').strip()
            open_id = dev.get('open_id', '').strip()
            if gitlab_username and open_id:
                username_map[gitlab_username] = open_id
        return username_map

    # 获取 developer 用户信息
    def get_all_developers(self) -> List[Dict]:
        return self.developers

    def get_openid_by_author(self, author: str) -> Optional[str]:
        """
        根据作者名称获取飞书open_id
        :param author: 作者名称（可能是GitLab用户名或显示名称）
        :return: open_id或None
        """
        if not author:
            return None

        author = author.strip()
        open_id = self.gitlab_username_to_openid_map.get(author)
        if open_id:
            return open_id

        logger.warning(f"无法匹配 gitlab 作者 {author} 的飞书open_id")
        return None
