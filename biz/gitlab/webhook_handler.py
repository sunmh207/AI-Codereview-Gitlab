import json
import os
import re
import time
from typing import Optional, Dict, List
from urllib.parse import urljoin
import fnmatch
import requests

from biz.utils.log import logger


def filter_changes(changes: list, project_config: Optional[Dict[str, str]] = None):
    '''
    过滤数据，只保留支持的文件类型以及必要的字段信息
    :param changes: 变更列表
    :param project_config: 项目专属配置字典
    '''
    # 从项目配置中获取支持的文件扩展名
    project_config = project_config or {}
    supported_extensions = project_config.get('SUPPORTED_EXTENSIONS', '.java,.py,.php').split(',')

    filter_deleted_files_changes = [change for change in changes if not change.get("deleted_file")]

    # 过滤 `new_path` 以支持的扩展名结尾的元素, 仅保留diff和new_path字段
    filtered_changes = [
        {
            'diff': item.get('diff', ''),
            'new_path': item['new_path'],
            'additions': len(re.findall(r'^\+(?!\+\+)', item.get('diff', ''), re.MULTILINE)),
            'deletions': len(re.findall(r'^-(?!--)', item.get('diff', ''), re.MULTILINE))
        }
        for item in filter_deleted_files_changes
        if any(item.get('new_path', '').endswith(ext) for ext in supported_extensions)
    ]
    return filtered_changes


def slugify_url(original_url: str) -> str:
    """
    将原始URL转换为适合作为文件名的字符串，其中非字母或数字的字符会被替换为下划线，举例：
    slugify_url("http://example.com/path/to/repo/") => example_com_path_to_repo
    slugify_url("https://gitlab.com/user/repo.git") => gitlab_com_user_repo_git
    """
    # Remove URL scheme (http, https, etc.) if present
    original_url = re.sub(r'^https?://', '', original_url)

    # Replace non-alphanumeric characters (except underscore) with underscores
    target = re.sub(r'[^a-zA-Z0-9]', '_', original_url)

    # Remove trailing underscore if present
    target = target.rstrip('_')

    return target


class MergeRequestHandler:
    def __init__(self, webhook_data: dict, gitlab_token: str, gitlab_url: str):
        self.merge_request_iid = None
        self.webhook_data = webhook_data
        self.gitlab_token = gitlab_token
        self.gitlab_url = gitlab_url
        self.event_type = None
        self.project_id = None
        self.action = None
        self.parse_event_type()

    def parse_event_type(self):
        # 提取 event_type
        self.event_type = self.webhook_data.get('object_kind', None)
        if self.event_type == 'merge_request':
            self.parse_merge_request_event()

    def parse_merge_request_event(self):
        # 提取 Merge Request 的相关参数
        merge_request = self.webhook_data.get('object_attributes', {})
        self.merge_request_iid = merge_request.get('iid')
        self.project_id = merge_request.get('target_project_id')
        self.action = merge_request.get('action')

    def is_author_excluded(self, excluded_users: Optional[list] = None) -> bool:
        """
        检查MR的作者是否在排除列表中
        :param excluded_users: 排除的用户名列表，如 ['howbuyscm', 'admin']
        :return: True表示作者在排除列表中，False表示不在
        """
        if not excluded_users:
            excluded_users = ['howbuyscm']  # 默认排除用户
        
        author_username = self.webhook_data.get('user', {}).get('username', '')
        if author_username in excluded_users:
            logger.info(f"MR author '{author_username}' is in excluded users list. Skipping review.")
            return True
        return False

    def get_merge_request_changes(self) -> list:
        # 检查是否为 Merge Request Hook 事件
        if self.event_type != 'merge_request':
            logger.warn(f"Invalid event type: {self.event_type}. Only 'merge_request' event is supported now.")
            return []

        # Gitlab merge request changes API可能存在延迟，多次尝试
        max_retries = 3  # 最大重试次数
        retry_delay = 10  # 重试间隔时间（秒）
        for attempt in range(max_retries):
            # 调用 GitLab API 获取 Merge Request 的 changes
            url = urljoin(f"{self.gitlab_url}/",
                          f"api/v4/projects/{self.project_id}/merge_requests/{self.merge_request_iid}/changes?access_raw_diffs=true")
            headers = {
                'Private-Token': self.gitlab_token
            }
            response = requests.get(url, headers=headers, verify=False)
            logger.debug(
                f"Get changes response from GitLab (attempt {attempt + 1}): {response.status_code}, {response.text}, URL: {url}")

            # 检查请求是否成功
            if response.status_code == 200:
                changes = response.json().get('changes', [])
                if changes:
                    return changes
                else:
                    logger.info(
                        f"Changes is empty, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries}), URL: {url}")
                    time.sleep(retry_delay)
            else:
                logger.warn(f"Failed to get changes from GitLab (URL: {url}): {response.status_code}, {response.text}")
                return []

        logger.warning(f"Max retries ({max_retries}) reached. Changes is still empty.")
        return []  # 达到最大重试次数后返回空列表

    def get_merge_request_commits(self) -> list:
        # 检查是否为 Merge Request Hook 事件
        if self.event_type != 'merge_request':
            return []

        # 调用 GitLab API 获取 Merge Request 的 commits
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/merge_requests/{self.merge_request_iid}/commits")
        headers = {
            'Private-Token': self.gitlab_token
        }
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(f"Get commits response from gitlab: {response.status_code}, {response.text}")
        # 检查请求是否成功
        if response.status_code == 200:
            return response.json()
        else:
            logger.warn(f"Failed to get commits: {response.status_code}, {response.text}")
            return []

    def add_merge_request_notes(self, review_result):
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/merge_requests/{self.merge_request_iid}/notes")
        headers = {
            'Private-Token': self.gitlab_token,
            'Content-Type': 'application/json'
        }
        data = {
            'body': review_result
        }
        response = requests.post(url, headers=headers, json=data, verify=False)
        logger.debug(f"Add notes to gitlab {url}: {response.status_code}, {response.text}")
        if response.status_code == 201:
            logger.info("Note successfully added to merge request.")
        else:
            logger.error(f"Failed to add note: {response.status_code}")
            logger.error(response.text)

    def get_merge_request_versions(self) -> List[Dict]:
        """
        获取 MR 的版本信息，用于行级评论定位
        返回包含 base_commit_sha, head_commit_sha, start_commit_sha 的版本列表
        """
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/merge_requests/{self.merge_request_iid}/versions")
        headers = {
            'Private-Token': self.gitlab_token
        }
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(f"Get MR versions response: {response.status_code}, {response.text}")
        if response.status_code == 200:
            return response.json()
        else:
            logger.warn(f"Failed to get MR versions: {response.status_code}, {response.text}")
            return []

    def add_merge_request_discussion(self, body: str, file_path: str, new_line: int, 
                                      base_sha: str, head_sha: str, start_sha: str,
                                      old_line: Optional[int] = None) -> bool:
        """
        在 MR 的指定代码行上创建讨论（行级评论）
        
        :param body: 评论内容
        :param file_path: 文件路径
        :param new_line: 新版本中的行号
        :param base_sha: 基础提交 SHA
        :param head_sha: 头部提交 SHA  
        :param start_sha: 起始提交 SHA
        :param old_line: 旧版本中的行号（可选，用于评论被删除的行）
        :return: 是否成功
        """
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/merge_requests/{self.merge_request_iid}/discussions")
        headers = {
            'Private-Token': self.gitlab_token,
            'Content-Type': 'application/json'
        }
        
        position = {
            'base_sha': base_sha,
            'head_sha': head_sha,
            'start_sha': start_sha,
            'position_type': 'text',
            'new_path': file_path,
            'old_path': file_path,
        }
        
        # 如果是新增的行，只设置 new_line
        # 如果是删除的行，只设置 old_line
        # 如果是修改的行，两者都设置
        if new_line:
            position['new_line'] = new_line
        if old_line:
            position['old_line'] = old_line
            
        data = {
            'body': body,
            'position': position
        }
        
        response = requests.post(url, headers=headers, json=data, verify=False)
        logger.debug(f"Add discussion to gitlab {url}: {response.status_code}, {response.text}")
        
        if response.status_code == 201:
            logger.info(f"Discussion successfully added to {file_path}:{new_line or old_line}")
            return True
        else:
            logger.error(f"Failed to add discussion: {response.status_code}, {response.text}")
            return False

    def add_line_level_comments(self, line_comments: List[Dict]) -> int:
        """
        批量添加行级评论
        
        :param line_comments: 行级评论列表，每个元素包含:
            - file_path: 文件路径
            - line_number: 行号
            - comment: 评论内容
            - severity: 严重程度 (可选: critical, warning, suggestion, info)
        :return: 成功添加的评论数量
        """
        # 获取 MR 版本信息
        versions = self.get_merge_request_versions()
        if not versions:
            logger.error("无法获取 MR 版本信息，无法添加行级评论")
            return 0
        
        # 使用最新版本
        latest_version = versions[0]
        base_sha = latest_version.get('base_commit_sha')
        head_sha = latest_version.get('head_commit_sha')
        start_sha = latest_version.get('start_commit_sha')
        
        if not all([base_sha, head_sha, start_sha]):
            logger.error(f"版本信息不完整: base={base_sha}, head={head_sha}, start={start_sha}")
            return 0
        
        success_count = 0
        for comment in line_comments:
            file_path = comment.get('file_path', '')
            line_number = comment.get('line_number', 0)
            comment_body = comment.get('comment', '')
            severity = comment.get('severity', 'info')
            
            if not all([file_path, line_number, comment_body]):
                logger.warn(f"跳过无效评论: {comment}")
                continue
            
            # 根据严重程度添加前缀标记
            severity_prefix = {
                'critical': '🚨 **严重问题**',
                'warning': '⚠️ **警告**',
                'suggestion': '💡 **建议**',
                'info': 'ℹ️ **提示**'
            }.get(severity, 'ℹ️ **提示**')
            
            formatted_body = f"{severity_prefix}\n\n{comment_body}"
            
            if self.add_merge_request_discussion(
                body=formatted_body,
                file_path=file_path,
                new_line=line_number,
                base_sha=base_sha,
                head_sha=head_sha,
                start_sha=start_sha
            ):
                success_count += 1
        
        logger.info(f"成功添加 {success_count}/{len(line_comments)} 条行级评论")
        return success_count

    def target_branch_protected(self) -> bool:
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/protected_branches")
        headers = {
            'Private-Token': self.gitlab_token,
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(f"Get protected branches response from gitlab: {response.status_code}, {response.text}")
        # 检查请求是否成功
        if response.status_code == 200:
            data = response.json()
            target_branch = self.webhook_data['object_attributes']['target_branch']
            return any(fnmatch.fnmatch(target_branch, item['name']) for item in data)
        else:
            logger.warn(f"Failed to get protected branches: {response.status_code}, {response.text}")
            return False


class PushHandler:
    def __init__(self, webhook_data: dict, gitlab_token: str, gitlab_url: str):
        self.webhook_data = webhook_data
        self.gitlab_token = gitlab_token
        self.gitlab_url = gitlab_url
        self.event_type = None
        self.project_id = None
        self.branch_name = None
        self.commit_list = []
        self.parse_event_type()

    def parse_event_type(self):
        # 提取 event_type
        self.event_type = self.webhook_data.get('event_name', None)
        if self.event_type == 'push':
            self.parse_push_event()

    def parse_push_event(self):
        # 提取 Push 事件的相关参数
        self.project_id = self.webhook_data.get('project_id', None)
        if self.project_id is None:
            self.project_id = self.webhook_data.get('project', {}).get('id')
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
        # 添加评论到 GitLab Push 请求的提交中（此处假设是在最后一次提交上添加注释）
        if not self.commit_list:
            logger.warn("No commits found to add notes to.")
            return ''

        # 获取最后一个提交的ID
        last_commit_id = self.commit_list[-1].get('id')
        if not last_commit_id:
            logger.error("Last commit ID not found.")
            return ''

        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/repository/commits/{last_commit_id}/comments")
        headers = {
            'Private-Token': self.gitlab_token,
            'Content-Type': 'application/json'
        }
        data = {
            'note': message
        }
        response = requests.post(url, headers=headers, json=data, verify=False)
        logger.debug(f"Add comment to commit {last_commit_id}: {response.status_code}, {response.text}")
        if response.status_code == 201:
            logger.info("Comment successfully added to push commit.")
            # 返回commit的URL，用户可以在这里查看评论
            commit_url = self.commit_list[-1].get('url', '')
            return commit_url
        else:
            logger.error(f"Failed to add comment: {response.status_code}")
            logger.error(response.text)
            return ''

    def __repository_commits(self, ref_name: str = "", since: str = "", until: str = "", pre_page: int = 100,
                             page: int = 1):
        # 获取仓库提交信息
        url = f"{urljoin(f'{self.gitlab_url}/', f'api/v4/projects/{self.project_id}/repository/commits')}?ref_name={ref_name}&since={since}&until={until}&per_page={pre_page}&page={page}"
        headers = {
            'Private-Token': self.gitlab_token
        }
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(
            f"Get commits response from GitLab for repository_commits: {response.status_code}, {response.text}, URL: {url}")

        if response.status_code == 200:
            return response.json()
        else:
            logger.warn(
                f"Failed to get commits for ref {ref_name}: {response.status_code}, {response.text}")
            return []

    def get_parent_commit_id(self, commit_id: str) -> str:
        commits = self.__repository_commits(ref_name=commit_id, pre_page=1, page=1)
        if commits and commits[0].get('parent_ids', []):
            return commits[0].get('parent_ids', [])[0]
        return ""

    def repository_compare(self, before: str, after: str):
        # 比较两个提交之间的差异
        url = f"{urljoin(f'{self.gitlab_url}/', f'api/v4/projects/{self.project_id}/repository/compare')}?from={before}&to={after}"
        headers = {
            'Private-Token': self.gitlab_token
        }
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(
            f"Get changes response from GitLab for repository_compare: {response.status_code}, {response.text}, URL: {url}")

        if response.status_code == 200:
            return response.json().get('diffs', [])
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
        headers = {
            'Private-Token': self.gitlab_token
        }

        # 优先尝试compare API获取变更
        before = self.webhook_data.get('before', '')
        after = self.webhook_data.get('after', '')
        if before and after:
            if after.startswith('0000000'):
                # 删除分支处理
                return []
            if before.startswith('0000000'):
                # 创建分支处理
                first_commit_id = self.commit_list[0].get('id')
                parent_commit_id = self.get_parent_commit_id(first_commit_id)
                if parent_commit_id:
                    before = parent_commit_id
            return self.repository_compare(before, after)
        else:
            return []


class NoteHandler:
    """
    处理 GitLab Note Hook 事件（评论事件）
    支持通过 @机器人 触发代码审查
    支持 MR 评论和 Commit 评论
    """
    def __init__(self, webhook_data: dict, gitlab_token: str, gitlab_url: str):
        self.webhook_data = webhook_data
        self.gitlab_token = gitlab_token
        self.gitlab_url = gitlab_url
        self.event_type = None
        self.project_id = None
        self.merge_request_iid = None
        self.commit_id = None
        self.note_content = None
        self.noteable_type = None
        self.parse_event()

    def parse_event(self):
        """解析 Note Hook 事件"""
        self.event_type = self.webhook_data.get('object_kind', None)
        if self.event_type == 'note':
            object_attributes = self.webhook_data.get('object_attributes', {})
            self.note_content = object_attributes.get('note', '')
            self.noteable_type = object_attributes.get('noteable_type', '')
            self.note_type = object_attributes.get('type', '')  # DiffNote or Note
            self.project_id = self.webhook_data.get('project', {}).get('id')
            
            # 如果是 MR 上的评论
            if self.noteable_type == 'MergeRequest':
                merge_request = self.webhook_data.get('merge_request', {})
                self.merge_request_iid = merge_request.get('iid')
            
            # 如果是 Commit 上的评论
            elif self.noteable_type == 'Commit':
                commit = self.webhook_data.get('commit', {})
                self.commit_id = commit.get('id')

    def is_diff_note(self) -> bool:
        """检查是否是代码行上的评论"""
        return self.note_type == 'DiffNote'

    def is_triggered_by_mention(self, bot_usernames: List[str] = None) -> bool:
        """
        检查评论是否通过 @机器人用户名 触发
        
        :param bot_usernames: 机器人用户名列表（不含@符号），如 ['code-review-bot', 'ai-reviewer']
        :return: True 表示评论中 @了机器人
        """
        if not self.note_content:
            return False
        
        if not bot_usernames:
            # 默认机器人用户名
            bot_usernames = ['code-review-bot', 'ai-reviewer', 'codereview']
        
        # 检查评论中是否 @了机器人
        for username in bot_usernames:
            # 支持 @username 格式
            if f'@{username}' in self.note_content.lower():
                logger.info(f"检测到 @{username} 触发代码审查")
                return True
        
        return False

    def is_merge_request_note(self) -> bool:
        """检查是否是 MR 上的评论"""
        return self.noteable_type == 'MergeRequest' and self.merge_request_iid is not None

    def is_commit_note(self) -> bool:
        """检查是否是 Commit 上的评论"""
        return self.noteable_type == 'Commit' and self.commit_id is not None

    def get_commit_diff(self) -> list:
        """获取 Commit 的代码变更"""
        if not self.is_commit_note():
            logger.warn("Not a commit note, cannot get diff")
            return []
        
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/repository/commits/{self.commit_id}/diff")
        headers = {
            'Private-Token': self.gitlab_token
        }
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(f"Get commit diff response: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warn(f"Failed to get commit diff: {response.status_code}, {response.text}")
            return []

    def get_commit_info(self) -> dict:
        """获取 Commit 的详细信息"""
        if not self.is_commit_note():
            return {}
        
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/repository/commits/{self.commit_id}")
        headers = {
            'Private-Token': self.gitlab_token
        }
        response = requests.get(url, headers=headers, verify=False)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warn(f"Failed to get commit info: {response.status_code}, {response.text}")
            return {}

    def add_commit_notes(self, note: str) -> str:
        """添加 Commit 评论，返回评论 URL"""
        if not self.is_commit_note():
            return ''
        
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/repository/commits/{self.commit_id}/comments")
        headers = {
            'Private-Token': self.gitlab_token,
            'Content-Type': 'application/json'
        }
        data = {
            'note': note
        }
        response = requests.post(url, headers=headers, json=data, verify=False)
        
        if response.status_code == 201:
            logger.info("Review result successfully added to commit.")
            # 返回 commit URL
            project_path = self.webhook_data.get('project', {}).get('path_with_namespace', '')
            return f"{self.gitlab_url}{project_path}/-/commit/{self.commit_id}"
        else:
            logger.error(f"Failed to add commit note: {response.status_code}, {response.text}")
            return ''

    def get_merge_request_changes(self) -> list:
        """获取 MR 的代码变更"""
        if not self.is_merge_request_note():
            logger.warn("Not a merge request note, cannot get changes")
            return []
        
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/merge_requests/{self.merge_request_iid}/changes?access_raw_diffs=true")
        headers = {
            'Private-Token': self.gitlab_token
        }
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(f"Get MR changes response: {response.status_code}")
        
        if response.status_code == 200:
            return response.json().get('changes', [])
        else:
            logger.warn(f"Failed to get MR changes: {response.status_code}, {response.text}")
            return []

    def get_merge_request_commits(self) -> list:
        """获取 MR 的提交记录"""
        if not self.is_merge_request_note():
            return []
        
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/merge_requests/{self.merge_request_iid}/commits")
        headers = {
            'Private-Token': self.gitlab_token
        }
        response = requests.get(url, headers=headers, verify=False)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warn(f"Failed to get MR commits: {response.status_code}, {response.text}")
            return []

    def get_merge_request_versions(self) -> List[Dict]:
        """获取 MR 的版本信息，用于行级评论定位"""
        if not self.is_merge_request_note():
            return []
        
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/merge_requests/{self.merge_request_iid}/versions")
        headers = {
            'Private-Token': self.gitlab_token
        }
        response = requests.get(url, headers=headers, verify=False)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warn(f"Failed to get MR versions: {response.status_code}, {response.text}")
            return []

    def add_merge_request_notes(self, review_result: str):
        """添加 MR 评论"""
        if not self.is_merge_request_note():
            return
        
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/merge_requests/{self.merge_request_iid}/notes")
        headers = {
            'Private-Token': self.gitlab_token,
            'Content-Type': 'application/json'
        }
        data = {
            'body': review_result
        }
        response = requests.post(url, headers=headers, json=data, verify=False)
        
        if response.status_code == 201:
            logger.info("Review result successfully added to merge request.")
        else:
            logger.error(f"Failed to add review note: {response.status_code}, {response.text}")

    def add_merge_request_discussion(self, body: str, file_path: str, new_line: int,
                                      base_sha: str, head_sha: str, start_sha: str,
                                      old_line: Optional[int] = None) -> bool:
        """在 MR 的指定代码行上创建讨论（行级评论）"""
        if not self.is_merge_request_note():
            return False
        
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/merge_requests/{self.merge_request_iid}/discussions")
        headers = {
            'Private-Token': self.gitlab_token,
            'Content-Type': 'application/json'
        }
        
        position = {
            'base_sha': base_sha,
            'head_sha': head_sha,
            'start_sha': start_sha,
            'position_type': 'text',
            'new_path': file_path,
            'old_path': file_path,
        }
        
        if new_line:
            position['new_line'] = new_line
        if old_line:
            position['old_line'] = old_line
            
        data = {
            'body': body,
            'position': position
        }
        
        response = requests.post(url, headers=headers, json=data, verify=False)
        
        if response.status_code == 201:
            logger.info(f"Discussion successfully added to {file_path}:{new_line or old_line}")
            return True
        else:
            logger.error(f"Failed to add discussion: {response.status_code}, {response.text}")
            return False

    def add_commit_discussion(self, body: str, file_path: str, line: int) -> bool:
        """在 Commit 的指定代码行上创建讨论（行级评论）"""
        if not self.is_commit_note():
            return False
            
        url = urljoin(f"{self.gitlab_url}/",
                      f"api/v4/projects/{self.project_id}/repository/commits/{self.commit_id}/discussions")
        headers = {
            'Private-Token': self.gitlab_token,
            'Content-Type': 'application/json'
        }
        
        data = {
            'body': body,
            'path': file_path,
            'line': line,
            'line_type': 'new'
        }
        
        response = requests.post(url, headers=headers, json=data, verify=False)
        
        if response.status_code == 201:
            logger.info(f"Commit discussion successfully added to {file_path}:{line}")
            return True
        else:
            logger.error(f"Failed to add commit discussion: {response.status_code}, {response.text}")
            return False

    def add_line_level_commit_comments(self, line_comments: List[Dict]) -> int:
        """批量添加 Commit 行级评论"""
        success_count = 0
        for comment in line_comments:
            file_path = comment.get('file_path', '')
            line_number = comment.get('line_number', 0)
            comment_body = comment.get('comment', '')
            severity = comment.get('severity', 'info')
            
            if not all([file_path, line_number, comment_body]):
                continue
            
            severity_prefix = {
                'critical': '🚨 **严重问题**',
                'warning': '⚠️ **警告**',
                'suggestion': '💡 **建议**',
                'info': 'ℹ️ **提示**'
            }.get(severity, 'ℹ️ **提示**')
            
            formatted_body = f"{severity_prefix}\n\n{comment_body}"
            
            if self.add_commit_discussion(
                body=formatted_body,
                file_path=file_path,
                line=line_number
            ):
                success_count += 1
        
        logger.info(f"成功添加 {success_count}/{len(line_comments)} 条 Commit 行级评论")
        return success_count

    def add_line_level_comments(self, line_comments: List[Dict]) -> int:
        """批量添加行级评论"""
        versions = self.get_merge_request_versions()
        if not versions:
            logger.error("无法获取 MR 版本信息，无法添加行级评论")
            return 0
        
        latest_version = versions[0]
        base_sha = latest_version.get('base_commit_sha')
        head_sha = latest_version.get('head_commit_sha')
        start_sha = latest_version.get('start_commit_sha')
        
        if not all([base_sha, head_sha, start_sha]):
            logger.error(f"版本信息不完整: base={base_sha}, head={head_sha}, start={start_sha}")
            return 0
        
        success_count = 0
        for comment in line_comments:
            file_path = comment.get('file_path', '')
            line_number = comment.get('line_number', 0)
            comment_body = comment.get('comment', '')
            severity = comment.get('severity', 'info')
            
            if not all([file_path, line_number, comment_body]):
                continue
            
            severity_prefix = {
                'critical': '🚨 **严重问题**',
                'warning': '⚠️ **警告**',
                'suggestion': '💡 **建议**',
                'info': 'ℹ️ **提示**'
            }.get(severity, 'ℹ️ **提示**')
            
            formatted_body = f"{severity_prefix}\n\n{comment_body}"
            
            if self.add_merge_request_discussion(
                body=formatted_body,
                file_path=file_path,
                new_line=line_number,
                base_sha=base_sha,
                head_sha=head_sha,
                start_sha=start_sha
            ):
                success_count += 1
        
        logger.info(f"成功添加 {success_count}/{len(line_comments)} 条行级评论")
        return success_count
