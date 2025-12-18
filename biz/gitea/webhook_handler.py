import os
import re
import time
from urllib.parse import urljoin

import fnmatch
import requests

from biz.utils.log import logger


def filter_changes(changes: list):
    """
    过滤数据，只保留支持的文件类型以及必要的字段信息
    """
    supported_extensions = [
        ext.strip() for ext in os.getenv('SUPPORTED_EXTENSIONS', '.java,.py,.php').split(',')
        if ext.strip()
    ]

    filtered_changes = []
    for item in changes:
        status = (item.get('status') or '').lower()
        if status in ('removed', 'deleted'):
            continue

        new_path = item.get('new_path') or item.get('filename') or item.get('path')
        if not new_path:
            continue

        if supported_extensions and not any(new_path.endswith(ext) for ext in supported_extensions):
            continue

        diff_text = item.get('diff') or item.get('patch') or ''
        additions = item.get('additions')
        deletions = item.get('deletions')

        if additions is None:
            additions = len(re.findall(r'^\+(?!\+\+)', diff_text, re.MULTILINE))
        if deletions is None:
            deletions = len(re.findall(r'^-(?!--)', diff_text, re.MULTILINE))

        filtered_changes.append({
            'diff': diff_text,
            'new_path': new_path,
            'additions': additions,
            'deletions': deletions
        })

    return filtered_changes


class PullRequestHandler:
    def __init__(self, webhook_data: dict, gitea_token: str, gitea_url: str):
        self.webhook_data = webhook_data
        self.gitea_token = gitea_token
        self.gitea_url = gitea_url.rstrip('/')
        self.event_type = None
        self.repo_full_name = None
        self.action = None
        self.pull_request_index = None
        self.target_branch = None

        self.parse_event_type()

    def _headers(self):
        return {
            'Authorization': f'token {self.gitea_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def parse_event_type(self):
        if self.webhook_data.get('pull_request'):
            self.event_type = 'pull_request'
            self.parse_pull_request_event()

    def parse_pull_request_event(self):
        pull_request = self.webhook_data.get('pull_request', {})
        repository = self.webhook_data.get('repository', {})

        self.action = self.webhook_data.get('action')
        self.pull_request_index = pull_request.get('number') or pull_request.get('index') or pull_request.get('id')

        owner_info = repository.get('owner', {})
        owner = owner_info.get('login') or owner_info.get('name') or owner_info.get('username')
        name = repository.get('name')
        self.repo_full_name = repository.get('full_name') or (f"{owner}/{name}" if owner and name else None)

        base_info = pull_request.get('base') or {}
        self.target_branch = base_info.get('ref') or pull_request.get('base_branch')

    def get_pull_request_changes(self) -> list:
        if self.event_type != 'pull_request':
            logger.warn(f"Invalid event type: {self.event_type}. Only 'pull_request' event is supported now.")
            return []

        if not self.repo_full_name or not self.pull_request_index:
            logger.error("Missing repository information for Gitea pull request.")
            return []

        max_retries = 3
        retry_delay = 10
        endpoint = f"api/v1/repos/{self.repo_full_name}/pulls/{self.pull_request_index}/files"
        url = urljoin(f"{self.gitea_url}/", endpoint)

        for attempt in range(max_retries):
            response = requests.get(url, headers=self._headers(), verify=False)
            logger.debug(
                f"Get changes response from Gitea (attempt {attempt + 1}): {response.status_code}, {response.text}, URL: {url}")

            if response.status_code == 200:
                files = response.json() or []
                if files:
                    changes = []
                    for file in files:
                        changes.append({
                            'diff': file.get('patch') or file.get('diff') or '',
                            'new_path': file.get('filename') or file.get('path') or '',
                            'status': file.get('status', ''),
                            'additions': file.get('additions'),
                            'deletions': file.get('deletions')
                        })
                    return changes
                logger.info(
                    f"Changes is empty, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries}), URL: {url}")
                time.sleep(retry_delay)
            else:
                logger.warn(f"Failed to get changes from Gitea (URL: {url}): {response.status_code}, {response.text}")
                return []

        logger.warning(f"Max retries ({max_retries}) reached. Changes is still empty.")
        return []

    def get_pull_request_commits(self) -> list:
        if self.event_type != 'pull_request':
            return []

        if not self.repo_full_name or not self.pull_request_index:
            logger.error("Missing repository information for retrieving Gitea pull request commits.")
            return []

        endpoint = f"api/v1/repos/{self.repo_full_name}/pulls/{self.pull_request_index}/commits"
        url = urljoin(f"{self.gitea_url}/", endpoint)
        response = requests.get(url, headers=self._headers(), verify=False)
        logger.debug(f"Get commits response from Gitea: {response.status_code}, {response.text}")

        if response.status_code == 200:
            commits = response.json() or []
            formatted_commits = []
            for commit in commits:
                commit_data = commit.get('commit', {})
                author_data = commit_data.get('author', {})
                formatted_commits.append({
                    'id': commit.get('sha') or commit.get('id'),
                    'title': (commit_data.get('message') or '').split('\n')[0],
                    'message': commit_data.get('message'),
                    'author_name': author_data.get('name'),
                    'author_email': author_data.get('email'),
                    'created_at': author_data.get('date') or commit.get('created_at'),
                    'web_url': commit.get('html_url') or commit.get('url')
                })
            return formatted_commits
        else:
            logger.warn(f"Failed to get commits from Gitea: {response.status_code}, {response.text}")
            return []

    def add_pull_request_notes(self, review_result: str):
        if not self.repo_full_name or not self.pull_request_index:
            logger.error("Missing repository information for adding pull request notes.")
            return

        endpoint = f"api/v1/repos/{self.repo_full_name}/issues/{self.pull_request_index}/comments"
        url = urljoin(f"{self.gitea_url}/", endpoint)
        response = requests.post(url, headers=self._headers(), json={'body': review_result}, verify=False)
        logger.debug(f"Add comment to Gitea pull request {url}: {response.status_code}, {response.text}")

        if response.status_code == 201:
            logger.info("Comment successfully added to Gitea pull request.")
        else:
            logger.error(f"Failed to add comment to Gitea pull request: {response.status_code}")
            logger.error(response.text)

    def target_branch_protected(self) -> bool:
        if not self.repo_full_name or not self.target_branch:
            return False

        endpoint = f"api/v1/repos/{self.repo_full_name}/branches?protected=true"
        url = urljoin(f"{self.gitea_url}/", endpoint)
        response = requests.get(url, headers=self._headers(), verify=False)
        logger.debug(f"Get protected branches response from Gitea: {response.status_code}, {response.text}")

        if response.status_code == 200:
            branches = response.json() or []
            return any(fnmatch.fnmatch(self.target_branch, branch.get('name', '')) for branch in branches)
        else:
            logger.warn(f"Failed to get protected branches from Gitea: {response.status_code}, {response.text}")
            return False


class PushHandler:
    def __init__(self, webhook_data: dict, gitea_token: str, gitea_url: str):
        self.webhook_data = webhook_data
        self.gitea_token = gitea_token
        self.gitea_url = gitea_url.rstrip('/')
        self.event_type = None
        self.repo_full_name = None
        self.branch_name = None
        self.commit_list = []

        self.parse_event_type()

    def _headers(self):
        return {
            'Authorization': f'token {self.gitea_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def parse_event_type(self):
        if self.webhook_data.get('ref'):
            self.event_type = 'push'
            self.parse_push_event()

    def parse_push_event(self):
        repository = self.webhook_data.get('repository', {})
        owner_info = repository.get('owner', {})
        owner = owner_info.get('login') or owner_info.get('name') or owner_info.get('username')
        name = repository.get('name')
        self.repo_full_name = repository.get('full_name') or (f"{owner}/{name}" if owner and name else None)

        self.branch_name = self.webhook_data.get('ref', '').replace('refs/heads/', '')
        self.commit_list = self.webhook_data.get('commits', [])

    def get_push_commits(self) -> list:
        if self.event_type != 'push':
            logger.warn(f"Invalid event type: {self.event_type}. Only 'push' event is supported now.")
            return []

        commit_details = []
        for commit in self.commit_list:
            commit_details.append({
                'message': commit.get('message'),
                'author': (commit.get('author') or {}).get('name'),
                'timestamp': commit.get('timestamp'),
                'url': commit.get('url'),
            })

        logger.info(f"Collected {len(commit_details)} commits from Gitea push event.")
        return commit_details

    def add_push_notes(self, message: str):
        # if not self.commit_list:
        #     logger.warn("No commits found to add comments to.")
        #     return

        # if not self.repo_full_name:
        #     logger.error("Missing repository information for adding push comments.")
        #     return

        # last_commit_id = self.commit_list[-1].get('id')
        # if not last_commit_id:
        #     logger.error("Last commit ID not found in Gitea push event.")
        #     return

        # endpoint = f"api/v1/repos/{self.repo_full_name}/git/commits/{last_commit_id}/comments"
        # url = urljoin(f"{self.gitea_url}/", endpoint)
        # response = requests.post(url, headers=self._headers(), json={'body': message}, verify=False)
        # logger.debug(f"Add comment to Gitea commit {last_commit_id}: {response.status_code}, {response.text}")

        # if response.status_code == 201:
        #     logger.info("Comment successfully added to Gitea commit.")
        # else:
        #     logger.error(f"Failed to add comment to Gitea commit: {response.status_code}")
        #     logger.error(response.text)

        # TODO 官方暂未提供添加评论的API，暂时先注释掉
        return

    def _get_commit_diff(self, commit_id: str) -> str:
        if not commit_id or not self.repo_full_name:
            return ""

        endpoint = f"api/v1/repos/{self.repo_full_name}/git/commits/{commit_id}.diff"
        url = urljoin(f"{self.gitea_url}/", endpoint)
        response = requests.get(url, headers=self._headers(), verify=False)
        logger.debug(
            f"Get commit diff from Gitea: {response.status_code}, {url}")
        if response.status_code == 200:
            return response.text or ""
        logger.warn(f"Failed to get commit diff from Gitea: {response.status_code}, {response.text}")
        return ""

    @staticmethod
    def _parse_diff_to_changes(diff_text: str) -> list:
        if not diff_text:
            return []

        changes = []
        current = None
        additions = deletions = 0
        lines_buffer = []
        new_path = ""
        status = ""

        def finalize():
            if current is None:
                return
            diff_str = "\n".join(lines_buffer)
            changes.append({
                'diff': diff_str,
                'new_path': new_path,
                'status': status,
                'additions': additions,
                'deletions': deletions
            })

        for line in diff_text.splitlines():
            if line.startswith('diff --git'):
                if current is not None:
                    finalize()
                current = True
                additions = deletions = 0
                lines_buffer = [line]
                new_path = ""
                status = ""
                continue

            if current is None:
                continue

            lines_buffer.append(line)

            if line.startswith('new file mode'):
                status = 'added'
            elif line.startswith('deleted file mode'):
                status = 'removed'
            elif line.startswith('+++ '):
                path = line[4:]
                if path.startswith('b/'):
                    path = path[2:]
                if path == '/dev/null':
                    path = ''
                new_path = path
            elif line.startswith('--- '):
                if status != 'removed' and line.endswith('/dev/null'):
                    status = 'removed'
            elif line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1

        if current is not None:
            finalize()

        return [change for change in changes if change.get('new_path')]

    def get_push_changes(self) -> list:
        if self.event_type != 'push':
            logger.warn(f"Invalid event type: {self.event_type}. Only 'push' event is supported now.")
            return []

        changes = []
        for commit in self.commit_list or []:
            commit_id = commit.get('id')
            diff_text = self._get_commit_diff(commit_id)
            changes.extend(self._parse_diff_to_changes(diff_text))
        return changes

