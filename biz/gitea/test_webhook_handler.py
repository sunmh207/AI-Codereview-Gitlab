#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2025/11/12
# @Author  : yuwenqiang
from unittest import TestCase, main

from biz.gitea.webhook_handler import PushHandler

# @Describe:
class TestPushHandler(TestCase):
    def setUp(self):
        """设置测试环境"""
        self.sample_webhook_data = {
            'repository': {
                'full_name': 'owner/repo'
            },
            'ref': 'refs/heads/main',
            'commits': [
                {
                    'id': 'commit123',
                    'message': 'Update mapper xml',
                    'author': {'name': 'Tester'},
                    'timestamp': '2025-11-12T15:00:00Z',
                    'url': 'https://gitea.example.com/owner/repo/commit/commit123'
                }
            ]
        }
        self.gitea_token = ''
        self.gitea_url = 'https://gitea.example.com'

        self.handler = PushHandler(self.sample_webhook_data, self.gitea_token, self.gitea_url)

    def test_get_push_commits(self):
        """测试获取提交信息"""
        commits = self.handler.get_push_commits()
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0]['message'], 'Update mapper xml')


if __name__ == '__main__':
    main()


