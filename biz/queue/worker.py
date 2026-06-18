import os
import traceback
from datetime import datetime

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.event.event_manager import event_manager
from biz.platforms.gitlab.webhook_handler import filter_changes, MergeRequestHandler, PushHandler
from biz.platforms.github.webhook_handler import filter_changes as filter_github_changes, PullRequestHandler as GithubPullRequestHandler, PushHandler as GithubPushHandler
from biz.platforms.gitea.webhook_handler import filter_changes as filter_gitea_changes, PullRequestHandler as GiteaPullRequestHandler, \
    PushHandler as GiteaPushHandler
from biz.service.review_service import ReviewService
from biz.utils.code_reviewer import CodeReviewer
from biz.utils.git_util import clone_branches_for_review, cleanup_repo
from biz.utils.im import notifier
from biz.utils.log import logger
from biz.utils.skill_reviewer import SkillReviewer


def review_gitlab_mr_with_skill(webhook_data: dict, gitlab_token: str,
                                source_branch: str, target_branch: str) -> str:
    """
    通过 Claude Code skill 审查 GitLab MR：克隆源/目标分支到临时目录，
    对 target...source 的增量运行 skill，返回 Markdown 结果。
    """
    git_http_url = webhook_data.get('project', {}).get('git_http_url', '')
    if not git_http_url:
        raise RuntimeError("webhook_data 缺少 project.git_http_url，无法克隆仓库进行 skill 审查。")

    repo_dir = None
    try:
        repo_dir, diff_range = clone_branches_for_review(
            git_http_url, gitlab_token, source_branch, target_branch
        )
        return SkillReviewer().review(repo_dir, diff_range)
    finally:
        if repo_dir:
            cleanup_repo(repo_dir)



def handle_push_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'
    try:
        handler = PushHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Push Hook event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        review_result = None
        score = 0
        additions = 0
        deletions = 0
        if push_review_enabled:
            # 获取PUSH的changes
            changes = handler.get_push_changes()
            logger.info('changes: %s', changes)
            changes = filter_changes(changes)
            if not changes:
                logger.info('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            review_result = "关注的文件没有修改"

            if len(changes) > 0:
                commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)
                score = CodeReviewer.parse_review_score(review_text=review_result)
                for item in changes:
                    additions += item['additions']
                    deletions += item['deletions']
            # 将review结果提交到Gitlab的 notes
            handler.add_push_notes(f'Auto Review Result: \n{review_result}')

        event_manager['push_reviewed'].send(PushReviewEntity(
            project_name=webhook_data['project']['name'],
            author=webhook_data['user_username'],
            branch=webhook_data.get('ref', '').replace('refs/heads/', ''),
            updated_at=int(datetime.now().timestamp()),  # 当前时间
            commits=commits,
            score=score,
            review_result=review_result,
            url_slug=gitlab_url_slug,
            webhook_data=webhook_data,
            additions=additions,
            deletions=deletions,
        ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_merge_request_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    '''
    处理Merge Request Hook事件
    :param webhook_data:
    :param gitlab_token:
    :param gitlab_url:
    :param gitlab_url_slug:
    :return:
    '''
    merge_review_only_protected_branches = os.environ.get('MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED', '0') == '1'
    try:
        # 解析Webhook数据
        handler = MergeRequestHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Merge Request Hook event received')

        # 新增：判断是否为draft（草稿）MR
        object_attributes = webhook_data.get('object_attributes', {})
        is_draft = object_attributes.get('draft') or object_attributes.get('work_in_progress')
        if is_draft:
            msg = f"[通知] MR为草稿（draft），未触发AI审查。\n项目: {webhook_data['project']['name']}\n作者: {webhook_data['user']['username']}\n源分支: {object_attributes.get('source_branch')}\n目标分支: {object_attributes.get('target_branch')}\n链接: {object_attributes.get('url')}"
            notifier.send_notification(content=msg)
            logger.info("MR为draft，仅发送通知，不触发AI review。")
            return

        # 如果开启了仅review projected branches的，判断当前目标分支是否为projected branches
        if merge_review_only_protected_branches and not handler.target_branch_protected():
            logger.info("Merge Request target branch not match protected branches, ignored.")
            return

        if handler.action not in ['open', 'update']:
            logger.info(f"Merge Request Hook event, action={handler.action}, ignored.")
            return

        # 检查last_commit_id是否已经存在，如果存在则跳过处理
        last_commit_id = object_attributes.get('last_commit', {}).get('id', '')
        if last_commit_id:
            project_name = webhook_data['project']['name']
            source_branch = object_attributes.get('source_branch', '')
            target_branch = object_attributes.get('target_branch', '')
            
            if ReviewService.check_mr_last_commit_id_exists(project_name, source_branch, target_branch, last_commit_id):
                logger.info(f"Merge Request with last_commit_id {last_commit_id} already exists, skipping review for {project_name}.")
                return

        # 仅仅在MR创建或更新时进行Code Review
        # 获取Merge Request的changes
        changes = handler.get_merge_request_changes()
        logger.info('changes: %s', changes)
        changes = filter_changes(changes)
        if not changes:
            logger.info('未检测到有关代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            return
        # 统计本次新增、删除的代码总数
        additions = 0
        deletions = 0
        for item in changes:
            additions += item.get('additions', 0)
            deletions += item.get('deletions', 0)

        # 获取Merge Request的commits
        commits = handler.get_merge_request_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # review 代码
        commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
        review_engine = os.environ.get('REVIEW_ENGINE', 'llm')
        if review_engine == 'skill':
            try:
                source_branch = object_attributes.get('source_branch', '')
                target_branch = object_attributes.get('target_branch', '')
                review_result = review_gitlab_mr_with_skill(
                    webhook_data, gitlab_token, source_branch, target_branch
                )
            except Exception as skill_err:
                # skill 审查失败(未登录/克隆失败等)时回退到 LLM diff 审查，保证 MR 仍有反馈
                logger.error(f'Skill 审查失败，回退到 LLM diff 审查: {skill_err}')
                review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)
        else:
            review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)

        # 计算评分(自动识别: 含"总分"的LLM报告按正则; skill 的 P0-P3 报告按权重扣分)
        score = CodeReviewer.compute_score(review_result)
        # skill 报告本身没有评分行, 在末尾附上评分摘要, 使 MR note 中可见
        if review_engine == 'skill' and '总分' not in review_result:
            c = CodeReviewer.count_skill_findings(review_result)
            review_result = (
                f"{review_result}\n\n---\n"
                f"**本次评分**: {score} 分　"
                f"(P0×{c['P0']} P1×{c['P1']} P2×{c['P2']} P3×{c['P3']})"
            )

        # 将review结果提交到Gitlab的 notes
        handler.add_merge_request_notes(f'Auto Review Result: \n{review_result}')

        # dispatch merge_request_reviewed event
        event_manager['merge_request_reviewed'].send(
            MergeRequestReviewEntity(
                project_name=webhook_data['project']['name'],
                author=webhook_data['user']['username'],
                source_branch=webhook_data['object_attributes']['source_branch'],
                target_branch=webhook_data['object_attributes']['target_branch'],
                updated_at=int(datetime.now().timestamp()),
                commits=commits,
                score=score,
                url=webhook_data['object_attributes']['url'],
                review_result=review_result,
                url_slug=gitlab_url_slug,
                webhook_data=webhook_data,
                additions=additions,
                deletions=deletions,
                last_commit_id=last_commit_id,
            )
        )

    except Exception as e:
        error_message = f'AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)

def handle_github_push_event(webhook_data: dict, github_token: str, github_url: str, github_url_slug: str):
    push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'
    try:
        handler = GithubPushHandler(webhook_data, github_token, github_url)
        logger.info('GitHub Push event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        review_result = None
        score = 0
        additions = 0
        deletions = 0
        if push_review_enabled:
            # 获取PUSH的changes
            changes = handler.get_push_changes()
            logger.info('changes: %s', changes)
            changes = filter_github_changes(changes)
            if not changes:
                logger.info('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            review_result = "关注的文件没有修改"

            if len(changes) > 0:
                commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)
                score = CodeReviewer.parse_review_score(review_text=review_result)
                for item in changes:
                    additions += item.get('additions', 0)
                    deletions += item.get('deletions', 0)
            # 将review结果提交到GitHub的 notes
            handler.add_push_notes(f'Auto Review Result: \n{review_result}')

        event_manager['push_reviewed'].send(PushReviewEntity(
            project_name=webhook_data['repository']['name'],
            author=webhook_data['sender']['login'],
            branch=webhook_data['ref'].replace('refs/heads/', ''),
            updated_at=int(datetime.now().timestamp()),  # 当前时间
            commits=commits,
            score=score,
            review_result=review_result,
            url_slug=github_url_slug,
            webhook_data=webhook_data,
            additions=additions,
            deletions=deletions,
        ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_github_pull_request_event(webhook_data: dict, github_token: str, github_url: str, github_url_slug: str):
    '''
    处理GitHub Pull Request 事件
    :param webhook_data:
    :param github_token:
    :param github_url:
    :param github_url_slug:
    :return:
    '''
    merge_review_only_protected_branches = os.environ.get('MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED', '0') == '1'
    try:
        # 解析Webhook数据
        handler = GithubPullRequestHandler(webhook_data, github_token, github_url)
        logger.info('GitHub Pull Request event received')
        # 如果开启了仅review projected branches的，判断当前目标分支是否为projected branches
        if merge_review_only_protected_branches and not handler.target_branch_protected():
            logger.info("Merge Request target branch not match protected branches, ignored.")
            return

        if handler.action not in ['opened', 'synchronize']:
            logger.info(f"Pull Request Hook event, action={handler.action}, ignored.")
            return

        # 检查GitHub Pull Request的last_commit_id是否已经存在，如果存在则跳过处理
        github_last_commit_id = webhook_data['pull_request']['head']['sha']
        if github_last_commit_id:
            project_name = webhook_data['repository']['name']
            source_branch = webhook_data['pull_request']['head']['ref']
            target_branch = webhook_data['pull_request']['base']['ref']
            
            if ReviewService.check_mr_last_commit_id_exists(project_name, source_branch, target_branch, github_last_commit_id):
                logger.info(f"Pull Request with last_commit_id {github_last_commit_id} already exists, skipping review for {project_name}.")
                return

        # 仅仅在PR创建或更新时进行Code Review
        # 获取Pull Request的changes
        changes = handler.get_pull_request_changes()
        logger.info('changes: %s', changes)
        changes = filter_github_changes(changes)
        if not changes:
            logger.info('未检测到有关代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            return
        # 统计本次新增、删除的代码总数
        additions = 0
        deletions = 0
        for item in changes:
            additions += item.get('additions', 0)
            deletions += item.get('deletions', 0)

        # 获取Pull Request的commits
        commits = handler.get_pull_request_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # review 代码
        commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
        review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)

        # 将review结果提交到GitHub的 notes
        handler.add_pull_request_notes(f'Auto Review Result: \n{review_result}')

        # dispatch pull_request_reviewed event
        event_manager['merge_request_reviewed'].send(
            MergeRequestReviewEntity(
                project_name=webhook_data['repository']['name'],
                author=webhook_data['pull_request']['user']['login'],
                source_branch=webhook_data['pull_request']['head']['ref'],
                target_branch=webhook_data['pull_request']['base']['ref'],
                updated_at=int(datetime.now().timestamp()),
                commits=commits,
                score=CodeReviewer.parse_review_score(review_text=review_result),
                url=webhook_data['pull_request']['html_url'],
                review_result=review_result,
                url_slug=github_url_slug,
                webhook_data=webhook_data,
                additions=additions,
                deletions=deletions,
                last_commit_id=github_last_commit_id,
            ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_gitea_push_event(webhook_data: dict, gitea_token: str, gitea_url: str, gitea_url_slug: str):
    push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'
    try:
        handler = GiteaPushHandler(webhook_data, gitea_token, gitea_url)
        logger.info('Gitea Push event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        review_result = None
        score = 0
        additions = 0
        deletions = 0
        if push_review_enabled:
            changes = handler.get_push_changes()
            logger.info('changes: %s', changes)
            changes = filter_gitea_changes(changes)
            if not changes:
                logger.info('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            review_result = "关注的文件没有修改"

            if len(changes) > 0:
                commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)
                score = CodeReviewer.parse_review_score(review_text=review_result)
                for item in changes:
                    additions += item.get('additions', 0)
                    deletions += item.get('deletions', 0)
            handler.add_push_notes(f'Auto Review Result: \n{review_result}')

        repository = webhook_data.get('repository', {})
        sender = webhook_data.get('sender', {}) or webhook_data.get('pusher', {}) or {}

        event_manager['push_reviewed'].send(PushReviewEntity(
            project_name=repository.get('name'),
            author=sender.get('login') or sender.get('username'),
            branch=handler.branch_name,
            updated_at=int(datetime.now().timestamp()),
            commits=commits,
            score=score,
            review_result=review_result,
            url_slug=gitea_url_slug,
            webhook_data=webhook_data,
            additions=additions,
            deletions=deletions,
        ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_gitea_pull_request_event(webhook_data: dict, gitea_token: str, gitea_url: str, gitea_url_slug: str):
    merge_review_only_protected_branches = os.environ.get('MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED', '0') == '1'
    try:
        handler = GiteaPullRequestHandler(webhook_data, gitea_token, gitea_url)
        logger.info('Gitea Pull Request event received')

        pull_request = webhook_data.get('pull_request', {})

        if merge_review_only_protected_branches and not handler.target_branch_protected():
            logger.info("Pull Request target branch not match protected branches, ignored.")
            return

        if handler.action not in ['opened', 'open', 'reopened', 'synchronize', 'synchronized']:
            logger.info(f"Pull Request Hook event, action={handler.action}, ignored.")
            return

        head_info = pull_request.get('head') or {}
        base_info = pull_request.get('base') or {}

        last_commit_id = head_info.get('sha') or pull_request.get('merge_commit_sha') or pull_request.get('last_commit_id')
        if last_commit_id:
            project_name = webhook_data.get('repository', {}).get('name')
            source_branch = head_info.get('ref') or pull_request.get('head_branch', '')
            target_branch = base_info.get('ref') or pull_request.get('base_branch', '')

            if ReviewService.check_mr_last_commit_id_exists(project_name, source_branch, target_branch, last_commit_id):
                logger.info(f"Pull Request with last_commit_id {last_commit_id} already exists, skipping review for {project_name}.")
                return

        changes = handler.get_pull_request_changes()
        logger.info('changes: %s', changes)
        changes = filter_gitea_changes(changes)
        if not changes:
            logger.info('未检测到有关代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            return

        additions = 0
        deletions = 0
        for item in changes:
            additions += item.get('additions', 0)
            deletions += item.get('deletions', 0)

        commits = handler.get_pull_request_commits()
        if not commits:
            logger.error('Failed to get commits for Gitea pull request')
            return

        commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
        review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)

        handler.add_pull_request_notes(f'Auto Review Result: \n{review_result}')

        repository = webhook_data.get('repository', {})
        author_info = pull_request.get('user', {}) or webhook_data.get('sender', {}) or {}

        event_manager['merge_request_reviewed'].send(
            MergeRequestReviewEntity(
                project_name=repository.get('name'),
                author=author_info.get('login') or author_info.get('username'),
                source_branch=head_info.get('ref') or pull_request.get('head_branch', ''),
                target_branch=base_info.get('ref') or pull_request.get('base_branch', ''),
                updated_at=int(datetime.now().timestamp()),
                commits=commits,
                score=CodeReviewer.parse_review_score(review_text=review_result),
                url=pull_request.get('html_url') or pull_request.get('url'),
                review_result=review_result,
                url_slug=gitea_url_slug,
                webhook_data=webhook_data,
                additions=additions,
                deletions=deletions,
                last_commit_id=last_commit_id,
            ))

    except Exception as e:
        error_message = f'AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)
