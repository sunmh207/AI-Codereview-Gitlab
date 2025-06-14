import os
import re
import time

import requests
import fnmatch
from biz.utils.log import logger



def filter_changes(changes: list):
    '''
    过滤数据，只保留支持的文件类型以及必要的字段信息
    专门处理GitHub格式的变更
    '''
    # 从环境变量中获取支持的文件扩展名
    supported_extensions = os.getenv('SUPPORTED_EXTENSIONS', '.java,.py,.php').split(',')
    
    # 筛选出未被删除的文件
    not_deleted_changes = []
    for change in changes:
        # 优先检查status字段是否为"removed"
        if change.get('status') == 'removed':
            logger.info(f"Detected file deletion via status field: {change.get('new_path')}")
            continue
            
        # 如果没有status字段或status不为"removed"，继续检查diff模式
        diff = change.get('diff', '')
        if diff:
            diff_header_match = re.match(r'@@ -\d+,\d+ \+0,0 @@', diff)
            if diff_header_match:
                # 检查除了diff头部外的所有行是否都以减号开头
                diff_lines = diff.split('\n')[1:]  # 跳过diff头部
                if all(line.startswith('-') or not line for line in diff_lines):
                    logger.info(f"Detected file deletion via diff pattern: {change.get('new_path')}")
                    continue
                    
        not_deleted_changes.append(change)
    
    logger.info(f"SUPPORTED_EXTENSIONS: {supported_extensions}")
    logger.info(f"After filtering deleted files: {not_deleted_changes}")
    
    # 过滤 `new_path` 以支持的扩展名结尾的元素, 仅保留diff和new_path字段
    filtered_changes = [
        {
            'diff': item.get('diff', ''),
            'new_path': item['new_path'],
            'additions': item.get('additions', 0),
            'deletions': item.get('deletions', 0),
        }
        for item in not_deleted_changes
        if any(item.get('new_path', '').endswith(ext) for ext in supported_extensions)
    ]
    logger.info(f"After filtering by extension: {filtered_changes}")
    return filtered_changes


class PullRequestHandler:
    def __init__(self, webhook_data: dict, github_token: str, github_url: str):
        self.pull_request_number = None
        self.webhook_data = webhook_data
        self.github_token = github_token
        self.github_url = github_url
        self.event_type = None
        self.repo_full_name = None
        self.action = None
        self.parse_event_type()

    def parse_event_type(self):
        # 提取 event_type
        self.event_type = 'pull_request'  # GitHub webhook 的事件类型通过 header 中的 X-GitHub-Event 获取，API 中已处理
        self.parse_pull_request_event()

    def parse_pull_request_event(self):
        # 提取 Pull Request 的相关参数
        self.pull_request_number = self.webhook_data.get('pull_request', {}).get('number')
        self.repo_full_name = self.webhook_data.get('repository', {}).get('full_name')
        self.action = self.webhook_data.get('action')

    def get_pull_request_changes(self) -> list:
        # 检查是否为 Pull Request Hook 事件
        if self.event_type != 'pull_request':
            logger.warn(f"Invalid event type: {self.event_type}. Only 'pull_request' event is supported now.")
            return []

        # GitHub pull request changes API可能存在延迟，多次尝试
        max_retries = 3  # 最大重试次数
        retry_delay = 10  # 重试间隔时间（秒）
        for attempt in range(max_retries):
            # 调用 GitHub API 获取 Pull Request 的 files（变更）
            url = f"https://api.github.com/repos/{self.repo_full_name}/pulls/{self.pull_request_number}/files"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            response = requests.get(url, headers=headers)
            logger.debug(
                f"Get changes response from GitHub (attempt {attempt + 1}): {response.status_code}, {response.text}, URL: {url}")

            # 检查请求是否成功
            if response.status_code == 200:
                files = response.json()
                if files:
                    # 转换成GitLab格式的changes
                    changes = []
                    for file in files:
                        change = {
                            'old_path': file.get('filename'),
                            'new_path': file.get('filename'),
                            'diff': file.get('patch', ''),
                            'additions': file.get('additions', 0),
                            'deletions': file.get('deletions', 0)
                        }
                        changes.append(change)
                    return changes
                else:
                    logger.info(
                        f"Changes is empty, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries}), URL: {url}")
                    time.sleep(retry_delay)
            else:
                logger.warn(f"Failed to get changes from GitHub (URL: {url}): {response.status_code}, {response.text}")
                return []

        logger.warning(f"Max retries ({max_retries}) reached. Changes is still empty.")
        return []  # 达到最大重试次数后返回空列表

    def get_pull_request_commits(self) -> list:
        # 检查是否为 Pull Request Hook 事件
        if self.event_type != 'pull_request':
            return []

        # 调用 GitHub API 获取 Pull Request 的 commits
        url = f"https://api.github.com/repos/{self.repo_full_name}/pulls/{self.pull_request_number}/commits"
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        response = requests.get(url, headers=headers)
        logger.debug(f"Get commits response from GitHub: {response.status_code}, {response.text}")
        
        # 检查请求是否成功
        if response.status_code == 200:
            # 将GitHub的commits转换为GitLab格式的commits
            github_commits = response.json()
            gitlab_format_commits = []
            for commit in github_commits:
                gitlab_commit = {
                    'id': commit.get('sha'),
                    'title': commit.get('commit', {}).get('message', '').split('\n')[0],
                    'message': commit.get('commit', {}).get('message', ''),
                    'author_name': commit.get('commit', {}).get('author', {}).get('name'),
                    'author_email': commit.get('commit', {}).get('author', {}).get('email'),
                    'created_at': commit.get('commit', {}).get('author', {}).get('date'),
                    'web_url': commit.get('html_url')
                }
                gitlab_format_commits.append(gitlab_commit)
            return gitlab_format_commits
        else:
            logger.warn(f"Failed to get commits: {response.status_code}, {response.text}")
            return []

    def add_pull_request_notes(self, review_result):
        url = f"https://api.github.com/repos/{self.repo_full_name}/issues/{self.pull_request_number}/comments"
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        data = {
            'body': review_result
        }
        response = requests.post(url, headers=headers, json=data)
        logger.debug(f"Add comment to GitHub PR {url}: {response.status_code}, {response.text}")
        if response.status_code == 201:
            logger.info("Comment successfully added to pull request.")
        else:
            logger.error(f"Failed to add comment: {response.status_code}")
            logger.error(response.text)

    def target_branch_protected(self) -> bool:
        url = f"https://api.github.com/repos/{self.repo_full_name}/branches?protected=true"
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            target_branch = self.webhook_data['pull_request']['base']['ref']
            return any(fnmatch.fnmatch(target_branch, item['name']) for item in data)
        else:
            logger.warn(f"Failed to get protected branches: {response.status_code}, {response.text}")
            return False


class PushHandler:
    def __init__(self, webhook_data: dict, github_token: str, github_url: str):
        self.webhook_data = webhook_data
        self.github_token = github_token
        self.github_url = github_url
        self.event_type = None
        self.repo_full_name = None
        self.branch_name = None
        self.commit_list = []
        self.parse_event_type()

    def parse_event_type(self):
        # 提取 event_type
        self.event_type = 'push'  # GitHub webhook 的事件类型通过 header 中的 X-GitHub-Event 获取，API 中已处理
        self.parse_push_event()

    def parse_push_event(self):
        # 提取 Push 事件的相关参数
        self.repo_full_name = self.webhook_data.get('repository', {}).get('full_name')
        self.branch_name = self.webhook_data.get('ref', '').replace('refs/heads/', '')
        self.commit_list = self.webhook_data.get('commits', [])

    def get_push_commits(self) -> list:
        # 检查是否为 Push 事件
        if self.event_type != 'push':
            logger.warn(f"Invalid event type: {self.event_type}. Only 'push' event is supported now.")
            return []

        # 提取提交信息
        commit_details = []
        for commit in self.commit_list:
            commit_info = {
                'message': commit.get('message'),
                'author': commit.get('author', {}).get('name'),
                'timestamp': commit.get('timestamp'),
                'url': commit.get('url'),
            }
            commit_details.append(commit_info)

        logger.info(f"Collected {len(commit_details)} commits from push event.")
        return commit_details

    def add_push_notes(self, message: str):
        # 添加评论到 GitHub Push 请求的提交中（此处假设是在最后一次提交上添加注释）
        if not self.commit_list:
            logger.warn("No commits found to add notes to.")
            return

        # 获取最后一个提交的ID
        last_commit_id = self.commit_list[-1].get('id')
        if not last_commit_id:
            logger.error("Last commit ID not found.")
            return

        url = f"https://api.github.com/repos/{self.repo_full_name}/commits/{last_commit_id}/comments"
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        data = {
            'body': message
        }
        response = requests.post(url, headers=headers, json=data)
        logger.debug(f"Add comment to commit {last_commit_id}: {response.status_code}, {response.text}")
        if response.status_code == 201:
            logger.info("Comment successfully added to push commit.")
        else:
            logger.error(f"Failed to add comment: {response.status_code}")
            logger.error(response.text)

    def __repository_commits(self, sha: str = "", per_page: int = 100, page: int = 1):
        # 获取仓库提交信息
        url = f"https://api.github.com/repos/{self.repo_full_name}/commits?sha={sha}&per_page={per_page}&page={page}"
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        response = requests.get(url, headers=headers)
        logger.debug(
            f"Get commits response from GitHub for repository_commits: {response.status_code}, {response.text}, URL: {url}")

        if response.status_code == 200:
            return response.json()
        else:
            logger.warn(
                f"Failed to get commits for sha {sha}: {response.status_code}, {response.text}")
            return []

    def get_parent_commit_id(self, commit_id: str) -> str:
        url = f"https://api.github.com/repos/{self.repo_full_name}/commits/{commit_id}"
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        response = requests.get(url, headers=headers)
        logger.debug(
            f"Get commit response from GitHub: {response.status_code}, {response.text}, URL: {url}")

        if response.status_code == 200 and response.json().get('parents'):
            return response.json().get('parents')[0].get('sha', '')
        return ""

    def repository_compare(self, base: str, head: str):
        # 比较两个提交之间的差异
        url = f"https://api.github.com/repos/{self.repo_full_name}/compare/{base}...{head}"
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        response = requests.get(url, headers=headers)
        logger.debug(
            f"Get changes response from GitHub for repository_compare: {response.status_code}, {response.text}, URL: {url}")

        if response.status_code == 200:
            # 转换为GitLab格式的diffs
            files = response.json().get('files', [])
            diffs = []
            for file in files:
                diff = {
                    'old_path': file.get('filename'),
                    'new_path': file.get('filename'),
                    'diff': file.get('patch', ''),
                    'status': file.get('status', ''),
                    'additions': file.get('additions', 0),
                    'deletions': file.get('deletions', 0),
                }
                diffs.append(diff)
            return diffs
        else:
            logger.warn(
                f"Failed to get changes for repository_compare: {response.status_code}, {response.text}")
            return []

    def get_push_changes(self) -> list:
        # 检查是否为 Push 事件
        if self.event_type != 'push':
            logger.warn(f"Invalid event type: {self.event_type}. Only 'push' event is supported now.")
            return []

        # 如果没有提交，返回空列表
        if not self.commit_list:
            logger.info("No commits found in push event.")
            return []

        # 优先尝试compare API获取变更
        before = self.webhook_data.get('before', '')
        after = self.webhook_data.get('after', '')
        if before and after:
            # GitHub没有0000000的写法，但我们可以检查是否是创建或删除分支事件
            if self.webhook_data.get('created', False):
                # 创建分支处理
                first_commit_id = self.commit_list[0].get('id')
                if first_commit_id:
                    parent_commit_id = self.get_parent_commit_id(first_commit_id)
                    if parent_commit_id:
                        before = parent_commit_id
            elif self.webhook_data.get('deleted', False):
                # 删除分支处理
                return []
            
            return self.repository_compare(before, after)
        else:
            # 如果before和after不存在，尝试通过commits获取
            logger.info("before or after not found in webhook data, trying to get changes from commits.")
            
            changes = []
            for commit in self.commit_list:
                commit_id = commit.get('id')
                if commit_id:
                    parent_id = self.get_parent_commit_id(commit_id)
                    if parent_id:
                        commit_changes = self.repository_compare(parent_id, commit_id)
                        changes.extend(commit_changes)
            
            return changes 