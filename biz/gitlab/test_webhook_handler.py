#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2025/3/18 17:58
# @Author  : Arrow
from unittest import TestCase, main

from biz.gitlab.webhook_handler import PushHandler


# @Describe:
class TestPushHandler(TestCase):
    def setUp(self):
        """设置测试环境"""
        self.sample_webhook_data = {
            'event_name': 'push',
            'project': {
                'id': 0
            },
        }
        self.gitlab_token = ''
        self.gitlab_url = ''

        # 创建PushHandler实例
        self.handler = PushHandler(self.sample_webhook_data, self.gitlab_token, self.gitlab_url)

    def test_get_parent_commit_id(self):
        """测试获取父提交ID"""
        commit_id = ''
        # 调用测试方法
        parent_id = self.handler.get_parent_commit_id(commit_id)

        self.assertTrue(parent_id)


if __name__ == '__main__':
    main()
