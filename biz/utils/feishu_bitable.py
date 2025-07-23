import os
import requests
import json
from datetime import datetime
from biz.utils.log import logger


class FeishuBitableClient:
    """飞书多维表格客户端"""

    def __init__(self, user_matcher=None):
        """
        初始化飞书多维表格客户端
        :param user_matcher: 用户匹配器实例，用于获取飞书open_id
        """
        self.app_id = os.environ.get('FEISHU_APP_ID', '')
        self.app_secret = os.environ.get('FEISHU_APP_SECRET', '')
        self.app_token = os.environ.get('FEISHU_BITABLE_APP_TOKEN', '')
        self.table_id = os.environ.get('FEISHU_BITABLE_TABLE_ID', '')
        self.report_table_id = os.environ.get('FEISHU_BITABLE_REPORT_TABLE_ID', '')
        self.enabled = os.environ.get('FEISHU_BITABLE_ENABLED', '0') == '1'
        self.base_url = 'https://open.feishu.cn/open-apis'
        self._access_token = None
        self._token_expires_at = 0

        # 用户匹配器，用于获取飞书用户信息
        self.user_matcher = user_matcher
        if user_matcher is None:
            # 延迟导入避免循环依赖
            try:
                from biz.utils.im.user_matcher import UserMatcher
                self.user_matcher = UserMatcher()
            except Exception as e:
                logger.warning(f"无法创建UserMatcher实例: {str(e)}")
                self.user_matcher = None

    def _get_access_token(self):
        """获取访问令牌"""
        if not self.app_id or not self.app_secret:
            logger.error("飞书应用ID或密钥未配置")
            return None

        # 检查token是否过期
        current_time = datetime.now().timestamp()
        if self._access_token and current_time < self._token_expires_at:
            return self._access_token

        # 获取新的access_token
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
            response.raise_for_status()

            result = response.json()
            if result.get('code') == 0:
                self._access_token = result.get('tenant_access_token')
                # 设置过期时间（提前5分钟过期）
                expires_in = result.get('expire', 7200)
                self._token_expires_at = current_time + expires_in - 300
                logger.info("飞书访问令牌获取成功")
                return self._access_token
            else:
                logger.error(f"获取飞书访问令牌失败: {result}")
                return None

        except Exception as e:
            logger.error(f"获取飞书访问令牌异常: {str(e)}")
            return None

    def _get_headers(self):
        """获取请求头"""
        access_token = self._get_access_token()
        if not access_token:
            return None

        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

    def create_record(self, fields):
        """
        创建多维表格记录

        Args:
            fields (dict): 字段数据，格式为 {"字段名": "值"}

        Returns:
            bool: 创建是否成功
        """
        if not self.enabled:
            logger.info("飞书多维表格功能未启用")
            return False

        if not self.app_token or not self.table_id:
            logger.error("飞书多维表格配置不完整，缺少app_token或table_id")
            return False

        headers = self._get_headers()
        if not headers:
            logger.error("无法获取飞书访问令牌")
            return False

        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"

        # 构造请求数据
        payload = {
            "fields": fields
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            result = response.json()
            if result.get('code') == 0:
                logger.info(f"飞书多维表格记录创建成功: {result.get('data', {}).get('record', {}).get('record_id')}")
                return True
            else:
                logger.error(f"飞书多维表格记录创建失败: {result}")
                return False

        except Exception as e:
            logger.error(f"飞书多维表格记录创建异常: {str(e)}")
            return False

    def create_push_review_record(self, entity):
        """
        为Push Review创建多维表格记录

        Args:
            entity (PushReviewEntity): Push Review实体对象

        Returns:
            bool: 创建是否成功
        """
        if not self.enabled:
            return False

        # 尝试获取飞书用户信息
        developer_field = self._get_developer_field_value(entity.author, self.user_matcher)

        # 构造字段数据
        fields = {
            "项目名称": entity.project_name,
            "开发者": entity.author,
            "分支": entity.branch,
            "更新时间": datetime.fromtimestamp(entity.updated_at).strftime("%Y-%m-%d %H:%M:%S"),
            "提交信息": entity.commit_messages,
            "评分": entity.score,
            "Review结果": entity.review_result or "无Review结果",
            # "新增行数": entity.additions,
            # "删除行数": entity.deletions,
            "CommitIds": entity.commit_ids,
            "Commit数量": len(entity.commits) if entity.commits else 0,
            "Review链接": {"link": entity.last_commit_url, "text": "查看详情"},
            "事件类型": "Push"
        }

        # 只有当 developer_field 不为 None 时才添加研发人员字段
        if developer_field is not None:
            fields["研发人员"] = developer_field

        return self.create_record(fields)

    def create_merge_request_review_record(self, entity):
        """
        为Merge Request Review创建多维表格记录

        Args:
            entity (MergeRequestReviewEntity): MR Review实体对象

        Returns:
            bool: 创建是否成功
        """
        if not self.enabled:
            return False

        # 尝试获取飞书用户信息
        developer_field = self._get_developer_field_value(entity.author, self.user_matcher)

        # 构造字段数据
        fields = {
            "项目名称": entity.project_name,
            "开发者": entity.author,
            "源分支": entity.source_branch,
            "目标分支": entity.target_branch,
            "更新时间": datetime.fromtimestamp(entity.updated_at).strftime("%Y-%m-%d %H:%M:%S"),
            "提交信息": entity.commit_messages,
            "评分": entity.score,
            "Review结果": entity.review_result or "无Review结果",
            "提交数量": len(entity.commits) if entity.commits else 0,
            "事件类型": "Merge Request",
            "MR链接": entity.url
        }

        # 只有当 developer_field 不为 None 时才添加研发人员字段
        if developer_field is not None:
            fields["研发人员"] = developer_field

        logger.info(f"准备向飞书多维表格插入MR Review数据: {entity.project_name} - {entity.author}")
        return self.create_record(fields)

    def create_daily_report_record(self, report_content: str, author: str) -> bool:
        """
        在多维表格中创建日报记录
        :param report_content: 日报内容
        :param author: 作者名称
        :return: 创建是否成功
        """
        if not self.app_token or not self.report_table_id:
            logger.error("飞书多维表格配置不完整，请配置 FEISHU_BITABLE_APP_TOKEN 和 FEISHU_BITABLE_REPORT_TABLE_ID")
            return False

        access_token = self._get_access_token()
        if not access_token:
            logger.error("无法获取飞书访问令牌")
            return False

        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.report_table_id}/records"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        developer_field = self._get_developer_field_value(author, self.user_matcher)

        # 构造记录数据
        record_data = {
            "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "开发者": author,
            "日报内容": report_content
        }

        # 只有当 developer_field 不为 None 时才添加研发人员字段
        if developer_field is not None:
            record_data["研发人员"] = developer_field

        payload = {
            "fields": record_data
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            result = response.json()

            if response.status_code != 200 or result.get('code') != 0:
                logger.error(f"创建多维表格记录失败: author={author}, error={result}")
                return False
            return True
        except Exception as e:
            logger.error(f"创建多维表格记录异常: author={author}, error={str(e)}")
            return False

    def _get_developer_field_value(self, author: str, user_matcher=None):
        """
        获取开发者字段的值，优先使用飞书用户ID格式
        :param author: 作者名称
        :param user_matcher: 用户匹配器实例
        :return: 开发者字段值
        """
        if user_matcher:
            try:
                open_id = user_matcher.get_openid_by_author(author)
                if open_id:
                    return [{"id": open_id}]
                else:
                    logger.info(f"未找到作者 {author} 的飞书open_id，使用原始名称")
            except Exception as e:
                logger.warning(f"获取作者 {author} 的飞书open_id时出错: {str(e)}")

        return None

    def test_connection(self):
        """
        测试飞书多维表格连接

        Returns:
            bool: 连接是否成功
        """
        if not self.enabled:
            logger.info("飞书多维表格功能未启用")
            return False

        access_token = self._get_access_token()
        if not access_token:
            logger.error("无法获取飞书访问令牌")
            return False

        if not self.app_token or not self.table_id:
            logger.error("飞书多维表格配置不完整")
            return False

        # 尝试获取表格信息来测试连接
        headers = self._get_headers()
        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            result = response.json()
            if result.get('code') == 0:
                logger.info("飞书多维表格连接测试成功")
                return True
            else:
                logger.error(f"飞书多维表格连接测试失败: {result}")
                return False

        except Exception as e:
            logger.error(f"飞书多维表格连接测试异常: {str(e)}")
            return False
