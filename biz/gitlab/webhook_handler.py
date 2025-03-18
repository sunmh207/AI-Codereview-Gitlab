import json
import time
from urllib.parse import urljoin

import requests

from biz.utils.log import logger
from biz.utils.i18n import get_translator
_ = get_translator()

class MergeRequestHandler:
    def __init__(self, webhook_data: dict, gitlab_token: str, gitlab_url: str):
        self.merge_request_iid = None
        self.webhook_data = webhook_data
        self.gitlab_token = gitlab_token
        self.gitlab_url = gitlab_url
        self.event_type = None
        self.merge_request_id = None
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

    def get_merge_request_changes(self) -> list:
        # 检查是否为 Merge Request Hook 事件
        if self.event_type != 'merge_request':
            logger.warn(_("Invalid event type: {}. Only 'merge_request' event is supported now.").format(self.event_type))
            return []

        # Gitlab merge request changes API可能存在延迟，多次尝试
        max_retries = 3  # 最大重试次数
        retry_delay = 10  # 重试间隔时间（秒）
        for attempt in range(max_retries):
            # 调用 GitLab API 获取 Merge Request 的 changes
            url = urljoin(f"{self.gitlab_url}/",
                          f"api/v4/projects/{self.project_id}/merge_requests/{self.merge_request_iid}/changes")
            headers = {
                'Private-Token': self.gitlab_token
            }
            response = requests.get(url, headers=headers, verify=False)
            logger.debug(
                _("Get changes response from GitLab (attempt {}): {}, {}, URL: {}").format(attempt + 1, response.status_code, response.text, url))
            # 检查请求是否成功
            if response.status_code == 200:
                changes = response.json().get('changes', [])
                if changes:
                    return changes
                else:
                    logger.info(
                        _("Changes is empty, retrying in {} seconds... (attempt {}/{}), URL: {}").format(retry_delay, attempt + 1, max_retries, url))
                    time.sleep(retry_delay)
            else:
                logger.warn(_("Failed to get changes from GitLab (URL: {}): {}, {}").format(url, response.status_code, response.text))
                return []

        logger.warning(_("Max retries ({}) reached. Changes is still empty.").format(max_retries))
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
        logger.debug(_("Get commits response from gitlab: {}, {}").format(response.status_code, response.text))  # 检查请求是否成功
        if response.status_code == 200:
            return response.json()
        else:
            logger.warn(_("Failed to get commits: {}, {}").format(response.status_code, response.text))
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
        logger.debug(_("Add notes to gitlab {}: {}, {}").format(url, response.status_code, response.text))
        if response.status_code == 201:
            logger.info("Note successfully added to merge request.")
        else:
            logger.error(_("Failed to add note: {}").format(response.status_code))
            logger.error(response.text)


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
        self.project_id = self.webhook_data.get('project', {}).get('id')
        self.branch_name = self.webhook_data.get('ref', '').replace('refs/heads/', '')
        self.commit_list = self.webhook_data.get('commits', [])

    def get_push_commits(self) -> list:
        # 检查是否为 Push 事件
        if self.event_type != 'push':
            logger.warn(_("Invalid event type: {}. Only 'push' event is supported now.").format(self.event_type))
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

        logger.info(_("Collected {} commits from push event.").format(len(commit_details)))
        return commit_details

    def add_push_notes(self, message: str):
        # 添加评论到 GitLab Push 请求的提交中（此处假设是在最后一次提交上添加注释）
        if not self.commit_list:
            logger.warn(_("No commits found to add notes to."))
            return

        # 获取最后一个提交的ID
        last_commit_id = self.commit_list[-1].get('id')
        if not last_commit_id:
            logger.error(_("Last commit ID not found."))
            return

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
        else:
            logger.error(f"Failed to add comment: {response.status_code}")
            logger.error(response.text)

    def get_push_changes(self) -> list:
        # 检查是否为 Push 事件
        if self.event_type != 'push':
            logger.warn(_("Invalid event type: {}. Only 'push' event is supported now.").format(self.event_type))
            return []

        # 如果没有提交，返回空列表
        if not self.commit_list:
            logger.info(_("No commits found in push event."))
            return []
        headers = {
            'Private-Token': self.gitlab_token
        }

        # 优先尝试compare API获取变更
        before = self.webhook_data.get('before', '')
        after = self.webhook_data.get('after', '')
        if before and after:
            url = f"{urljoin(f'{self.gitlab_url}/', f'api/v4/projects/{self.project_id}/repository/compare')}?from={before}&to={after}"

            response = requests.get(url, headers=headers, verify=False)
            logger.debug(
                _("Get changes response from GitLab for push event: {}, {}, URL: {}").format(response.status_code, response.text, url))
            if response.status_code == 200:
                return response.json().get('diffs', [])
            else:
                logger.warn(_("Failed to get changes for push event: {}, {}, URL: {}").format(response.status_code, response.text, url))
                return []
        else:
            return []

class SystemHookHandler:
    def __init__(self, webhook_data: dict, gitlab_token: str, gitlab_url: str):
        self.webhook_data = webhook_data
        self.gitlab_token = gitlab_token
        self.gitlab_url = gitlab_url
        self.event_type = None
        self.project_id = None
        self.changes = []
        self.parse_event_type()

    def parse_event_type(self):
        # Extract event_type
        self.event_type = self.webhook_data.get(_('event_name'), None)
        if self.event_type == _('repository_update'):
            self.parse_repository_update_event()

    def parse_repository_update_event(self):
        # Parse repository_update event parameters
        self.project_id = self.webhook_data.get('project', {}).get('id')
        self.changes = self.webhook_data.get('changes', [])

    def get_repository_changes(self) -> list:
        # Check if the event is repository_update
        if self.event_type != 'repository_update':
            logger.warn(_("Invalid event type: {}. Only 'repository_update' event is supported now.").format(self.event_type))
            return []

        if not self.changes:
            logger.warn(_("No changes found in webhook data."))
            return []

        headers = {'Private-Token': self.gitlab_token}
        all_diffs = []

        max_retries = 3  # Maximum retry attempts
        retry_delay = 10  # Retry delay in seconds

        for change in self.changes:
            before = change.get('before')
            after = change.get('after')
            ref = change.get('ref', _('unknown branch'))

            if not before or not after:
                logger.warn(_("Missing before or after commit ID for ref {}.").format(ref))
                continue

            url = f"{urljoin(f'{self.gitlab_url}/', f'api/v4/projects/{self.project_id}/repository/compare')}?from={before}&to={after}"

            for attempt in range(max_retries):
                response = requests.get(url, headers=headers, verify=False)
                logger.debug(
                    _("Get changes response from GitLab for repository_update (attempt {}): {}, {}, URL: {}").format(attempt + 1, response.status_code, response.text, url))

                if response.status_code == 200:
                    diffs = response.json().get('diffs', [])
                    if diffs:
                        all_diffs.extend(diffs)
                    break
                else:
                    logger.warn(
                        _("Failed to get changes for ref {}: {}, {}, retrying in {} seconds...").format(ref, response.status_code, response.text, retry_delay))
                    time.sleep(retry_delay)

        if not all_diffs:
            logger.warning(_("Max retries ({}) reached. Unable to retrieve repository changes.").format(max_retries))
        return all_diffs

    def get_repository_commits(self) -> list:
        # Get commits from repository_update event
        if self.event_type != _('repository_update'):
            logger.warn(_("Invalid event type: {}. Only 'repository_update' event is supported now.").format(self.event_type))
            return []

        if not self.changes:
            logger.warn(_("No changes found in webhook data."))
            return []

        headers = {'Private-Token': self.gitlab_token}
        all_commits = []

        for change in self.changes:
            before = change.get('before')
            after = change.get('after')
            ref = change.get('ref', _('unknown branch'))

            if not before or not after:
                logger.warn(_("Missing before or after commit ID for ref {}.").format(ref))
                continue

            url = f"{urljoin(f'{self.gitlab_url}/', f'api/v4/projects/{self.project_id}/repository/commits')}?ref_name={ref}"
            response = requests.get(url, headers=headers, verify=False)
            logger.debug(
                _("Get commits response from GitLab for repository_update: {}, {}, URL: {}").format(response.status_code, response.text, url))

            if response.status_code == 200:
                commits = response.json()
                if commits:
                    all_commits.extend(commits)
            else:
                logger.warn(
                    _("Failed to get commits for ref {}: {}, {}").format(ref, response.status_code, response.text))

        return all_commits