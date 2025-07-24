import unittest
from unittest.mock import patch, MagicMock
import json
import os
import tempfile
from datetime import datetime, timedelta

# 创建临时日志文件，避免目录不存在的问题
temp_log_file = tempfile.NamedTemporaryFile(delete=False, suffix='.log')
temp_log_file.close()

# 设置测试环境变量，避免依赖真实的.env文件
os.environ.setdefault('PUSH_REVIEW_ENABLED', '1')
os.environ.setdefault('GITLAB_URL', 'https://gitlab.example.com')
os.environ.setdefault('GITLAB_ACCESS_TOKEN', 'test_token')
os.environ.setdefault('LOG_FILE', temp_log_file.name)  # 使用临时日志文件

from api import api_app


class TestUsersWithoutReview(unittest.TestCase):

    def setUp(self):
        """测试前准备"""
        self.app = api_app.test_client()
        self.app.testing = True

    @patch('api.UserMatcher')
    @patch('api.ReviewService.get_push_review_authors_by_time')
    def test_users_without_review_all_time(self, mock_get_authors, mock_user_matcher):
        """测试获取历史所有时间范围内没有审查记录的用户"""
        # Mock 数据
        mock_get_authors.return_value = ['user1', 'user2']
        mock_matcher_instance = MagicMock()
        mock_matcher_instance.get_all_developers.return_value = [
            {'name': '张三', 'gitlab_username': 'user1'},
            {'name': '李四', 'gitlab_username': 'user2'},
            {'name': '王五', 'gitlab_username': 'user3'}
        ]
        mock_user_matcher.return_value = mock_matcher_instance

        response = self.app.get('/review/users_without_review')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['users_without_review']), 1)
        self.assertEqual(data['data']['users_without_review'][0]['gitlab_username'], 'user3')
        self.assertEqual(data['data']['total_developers'], 3)
        self.assertEqual(data['data']['review_coverage_rate'], 66.67)

    @patch('api.UserMatcher')
    @patch('api.ReviewService.get_push_review_authors_by_time')
    def test_users_without_review_today(self, mock_get_authors, mock_user_matcher):
        """测试获取当天没有审查记录的用户"""
        mock_get_authors.return_value = []
        mock_matcher_instance = MagicMock()
        mock_matcher_instance.get_all_developers.return_value = [
            {'name': '张三', 'gitlab_username': 'user1'}
        ]
        mock_user_matcher.return_value = mock_matcher_instance

        response = self.app.get('/review/users_without_review?time_range=today')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['users_without_review']), 1)
        self.assertEqual(data['data']['review_coverage_rate'], 0)

    @patch('api.UserMatcher')
    @patch('api.ReviewService.get_push_review_authors_by_time')
    def test_users_without_review_custom_time(self, mock_get_authors, mock_user_matcher):
        """测试自定义时间范围"""
        mock_get_authors.return_value = ['user1']
        mock_matcher_instance = MagicMock()
        mock_matcher_instance.get_all_developers.return_value = [
            {'name': '张三', 'gitlab_username': 'user1'}
        ]
        mock_user_matcher.return_value = mock_matcher_instance

        start_time = int(datetime.now().timestamp()) - 86400
        end_time = int(datetime.now().timestamp())

        response = self.app.get(f'/review/users_without_review?start_time={start_time}&end_time={end_time}')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['users_without_review']), 0)

    def test_invalid_time_range(self):
        """测试无效的时间范围参数"""
        response = self.app.get('/review/users_without_review?time_range=invalid')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('time_range 参数无效', data['message'])

    def test_invalid_timestamp(self):
        """测试无效的时间戳格式"""
        response = self.app.get('/review/users_without_review?start_time=invalid&end_time=123')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('时间戳格式错误', data['message'])

    @patch('api.UserMatcher')
    def test_no_developers_file(self, mock_user_matcher):
        """测试开发者文件不存在的情况"""
        mock_matcher_instance = MagicMock()
        mock_matcher_instance.get_all_developers.return_value = []
        mock_user_matcher.return_value = mock_matcher_instance

        response = self.app.get('/review/users_without_review')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(data['success'])
        self.assertIn('developer.json 文件不存在或为空', data['message'])

    @patch('api.UserMatcher')
    @patch('api.ReviewService.get_push_review_authors_by_time')
    def test_empty_gitlab_username(self, mock_get_authors, mock_user_matcher):
        """测试空的gitlab_username字段"""
        mock_get_authors.return_value = []
        mock_matcher_instance = MagicMock()
        mock_matcher_instance.get_all_developers.return_value = [
            {'name': '张三', 'gitlab_username': ''},
            {'name': '李四', 'gitlab_username': 'user2'}
        ]
        mock_user_matcher.return_value = mock_matcher_instance

        response = self.app.get('/review/users_without_review')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['total_developers'], 1)  # 只计算有效的开发者

    @patch('api.UserMatcher')
    @patch('api.ReviewService.get_push_review_authors_by_time')
    def test_exception_handling(self, mock_get_authors, mock_user_matcher):
        """测试异常处理"""
        mock_get_authors.side_effect = Exception("数据库连接错误")

        response = self.app.get('/review/users_without_review')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('分析用户代码审查记录时出错', data['message'])


if __name__ == '__main__':
    try:
        unittest.main()
    finally:
        # 清理临时日志文件
        if os.path.exists(temp_log_file.name):
            os.unlink(temp_log_file.name)
