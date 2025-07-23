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
        self.email_to_openid_map = self._create_email_mapping()

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

    def _create_email_mapping(self) -> Dict[str, str]:
        """创建邮箱到open_id的映射"""
        email_map = {}
        for user in self.feishu_users:
            email = user.get('email', '').strip().lower()
            open_id = user.get('open_id', '')
            if email and open_id:
                email_map[email] = open_id

        return email_map

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

        if open_id:
            logger.debug(f"通过姓名匹配到用户: {name} -> {open_id}")
        else:
            logger.debug(f"未找到姓名对应的用户: {name}")

        return open_id

    def get_openid_by_gitlab_user(self, gitlab_username: str = None, gitlab_name: str = None, gitlab_email: str = None) -> Optional[str]:
        """
        根据GitLab用户信息获取飞书open_id
        :param gitlab_username: GitLab用户名
        :param gitlab_name: GitLab显示名称
        :return: open_id或None
        """
        # 其次通过显示名称匹配
        if gitlab_name:
            open_id = self.get_openid_by_name(gitlab_name)
            if open_id:
                return open_id

        # 最后尝试通过用户名匹配（如果用户名就是中文名）
        if gitlab_username:
            open_id = self.get_openid_by_name(gitlab_username)
            if open_id:
                return open_id

        logger.warning(f"无法匹配GitLab用户: username={gitlab_username}, name={gitlab_name}")
        return None

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
            'email_mappings_count': len(self.email_to_openid_map)
        }
