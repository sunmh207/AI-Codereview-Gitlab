import os
import re
import traceback
from datetime import datetime

from typing import Dict, Optional

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.event.event_manager import event_manager
from biz.gitlab.webhook_handler import filter_changes, MergeRequestHandler, PushHandler, NoteHandler
from biz.github.webhook_handler import filter_changes as filter_github_changes, PullRequestHandler as GithubPullRequestHandler, PushHandler as GithubPushHandler
from biz.gitea.webhook_handler import filter_changes as filter_gitea_changes, PullRequestHandler as GiteaPullRequestHandler, \
    PushHandler as GiteaPushHandler
from biz.service.review_service import ReviewService
from biz.utils.code_reviewer import CodeReviewer, LineReviewer
from biz.utils.config_loader import config_loader
from biz.utils.im import notifier
from biz.utils.log import logger


def check_project_whitelist(project_path: str, project_config: Optional[Dict[str, str]] = None) -> bool:
    """
    检查项目是否在白名单中
    :param project_path: 项目路径，格式为 namespace/project_name（如：asset/asset-batch-center）
    :param project_config: 项目专属配置字典，优先级高于全局环境变量
    :return: True表示在白名单中，False表示不在白名单中
    """
    # 全局开关始终从os.environ读取
    whitelist_enabled = os.environ.get('REVIEW_WHITELIST_ENABLED', '0') == '1'
    if not whitelist_enabled:
        # 白名单功能未开启，所有项目都允许
        return True
    
    # 优先从project_config读取白名单列表
    whitelist_str = ''
    if project_config:
        whitelist_str = project_config.get('REVIEW_WHITELIST', '')
    
    # 降级到全局环境变量
    if not whitelist_str:
        whitelist_str = os.environ.get('REVIEW_WHITELIST', '')
    if not whitelist_str:
        logger.warning('白名单功能已开启但REVIEW_WHITELIST配置为空，将拒绝所有项目的Review')
        return False
    
    # 解析白名单配置（逗号分隔）
    whitelist_items = [item.strip() for item in whitelist_str.split(',') if item.strip()]
    
    if not project_path:
        logger.warning('项目路径为空，无法进行白名单检查')
        return False
    
    # 提取命名空间和项目名
    if '/' in project_path:
        namespace = project_path.split('/', 1)[0]
    else:
        # 如果没有/，则整个project_path就是命名空间
        namespace = project_path
    
    # 检查是否在白名单中
    for item in whitelist_items:
        # 完全匹配项目路径（如：asset/asset-batch-center）
        if item == project_path:
            logger.info(f'项目 {project_path} 在白名单中（完全匹配：{item}）')
            return True
        # 匹配命名空间（如：asset）
        if '/' not in item and item == namespace:
            logger.info(f'项目 {project_path} 在白名单中（命名空间匹配：{item}）')
            return True
    
    logger.info(f'项目 {project_path} 不在白名单中，跳过Review。白名单配置：{whitelist_str}')
    return False



def handle_push_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    # 初始化project_config为None，确保在异常处理中可以访问
    project_config = None
    try:
        # 提取项目路径
        project_path = webhook_data.get('project', {}).get('path_with_namespace', '')
        logger.info(f'Project path: {project_path}')
        
        # 加载项目专属配置（不修改全局环境变量）
        project_config = config_loader.get_config(project_path=project_path)
        
        # 检查白名单（传递project_config确保配置隔离）
        if not check_project_whitelist(project_path, project_config=project_config):
            logger.info(f'项目 {project_path} 不在白名单中，跳过Push Review')
            return
        logger.info(f'项目 {project_path} 使用独立配置上下文')
        
        # 从项目配置中读取 GITLAB_ACCESS_TOKEN
        gitlab_token = project_config.get('GITLAB_ACCESS_TOKEN') or gitlab_token
        
        # 检查是否启用Push Review
        push_review_enabled = project_config.get('PUSH_REVIEW_ENABLED', '0') == '1'
        
        handler = PushHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Push Hook event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # 检查是否启用了commit message检查
        commit_message_check_enabled = project_config.get('PUSH_COMMIT_MESSAGE_CHECK_ENABLED', '0') == '1'
        if commit_message_check_enabled:
            # 获取检查规则（支持正则表达式）
            check_pattern = project_config.get('PUSH_COMMIT_MESSAGE_CHECK_PATTERN', 'review')
            try:
                # 检查所有commits的message是否匹配正则表达式
                pattern = re.compile(check_pattern, re.IGNORECASE)
                has_match = any(pattern.search(commit.get('message', '')) for commit in commits)
                if not has_match:
                    logger.info(f'Commits message中未匹配到指定规则 "{check_pattern}"，跳过本次审查。')
                    return
                logger.info(f'Commits message匹配规则 "{check_pattern}"，继续执行审查。')
            except re.error as e:
                logger.error(f'正则表达式 "{check_pattern}" 格式错误: {e}，跳过检查继续执行。')

        review_result = ""
        score = 0
        additions = 0
        deletions = 0
        note_url = ''  # 存储AI Review结果的URL
        if push_review_enabled:
            # 获取PUSH的changes
            changes = handler.get_push_changes()
            logger.info('changes: %s', changes)
            changes = filter_changes(changes, project_config)
            if not changes:
                logger.info('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            review_result = "关注的文件没有修改"

            if len(changes) > 0:
                commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                review_result = CodeReviewer(project_path=project_path, config=project_config).review_and_strip_code(str(changes), commits_text)
                score = CodeReviewer.parse_review_score(review_text=review_result)
                for item in changes:
                    additions += item['additions']
                    deletions += item['deletions']
            # 将review结果提交到Gitlab的 notes
            note_url = handler.add_push_notes(f'Auto Review Result: \n{review_result}')

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
            note_url=note_url,
            project_config=project_config,
        ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        # 尝试获取project_config，如果异常发生在配置加载之前则为None
        try:
            notifier.send_notification(content=error_message, project_config=project_config)
        except NameError:
            notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_note_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    """
    处理 Note Hook 事件（@机器人触发的代码审查）
    
    :param webhook_data: GitLab Note Hook 的 payload
    :param gitlab_token: GitLab access token
    :param gitlab_url: GitLab URL
    :param gitlab_url_slug: GitLab URL slug
    """
    project_config = None
    try:
        # 提取项目路径
        project_path = webhook_data.get('project', {}).get('path_with_namespace', '')
        logger.info(f'Note event received for project: {project_path}')
        
        # 加载项目专属配置
        project_config = config_loader.get_config(project_path=project_path)
        
        # 检查是否启用 @触发功能（总开关）
        mention_trigger_enabled = project_config.get('MENTION_TRIGGER_ENABLED', '0') == '1'
        if not mention_trigger_enabled:
            logger.info("@触发功能未启用（MENTION_TRIGGER_ENABLED=0），跳过处理")
            return
        
        # 从项目配置中读取 GITLAB_ACCESS_TOKEN
        gitlab_token = project_config.get('GITLAB_ACCESS_TOKEN') or gitlab_token
        
        # 解析 Note Hook 数据
        handler = NoteHandler(webhook_data, gitlab_token, gitlab_url)
        
        # 获取机器人用户名配置（支持多个用户名，逗号分隔）
        bot_usernames_str = project_config.get('REVIEW_BOT_USERNAMES', 'code-review-bot,ai-reviewer,codereview')
        bot_usernames = [name.strip().lower() for name in bot_usernames_str.split(',') if name.strip()]
        
        # 检查评论作者是否为机器人自己，防止无限循环
        author_username = webhook_data.get('user', {}).get('username', '').lower()
        if author_username in bot_usernames:
            logger.info(f"检测到评论作者为机器人 ({author_username})，跳过处理以防止循环触发")
            return

        # 检查是否通过 @机器人 触发
        if not handler.is_triggered_by_mention(bot_usernames):
            logger.info("评论中未检测到 @机器人，跳过处理")
            return
        
        # 检查评论类型并分别处理
        if handler.is_merge_request_note():
            # MR 评论触发开关
            mr_mention_enabled = project_config.get('MENTION_TRIGGER_MR_ENABLED', '1') == '1'
            if not mr_mention_enabled:
                logger.info("MR @触发功能未启用（MENTION_TRIGGER_MR_ENABLED=0），跳过处理")
                return
            _handle_mr_note_review(handler, webhook_data, project_path, project_config, gitlab_url_slug)
            
        elif handler.is_commit_note():
            # Commit 评论触发开关
            commit_mention_enabled = project_config.get('MENTION_TRIGGER_COMMIT_ENABLED', '1') == '1'
            if not commit_mention_enabled:
                logger.info("Commit @触发功能未启用（MENTION_TRIGGER_COMMIT_ENABLED=0），跳过处理")
                return
            _handle_commit_note_review(handler, webhook_data, project_path, project_config, gitlab_url_slug)
            
        else:
            logger.info(f"不支持的评论类型: {handler.noteable_type}，跳过处理")
            return

    except Exception as e:
        error_message = f'@触发代码审查出现错误: {str(e)}\n{traceback.format_exc()}'
        try:
            notifier.send_notification(content=error_message, project_config=project_config)
        except NameError:
            notifier.send_notification(content=error_message)
        logger.error('处理 Note 事件出现错误: %s', error_message)


def _handle_mr_note_review(handler: NoteHandler, webhook_data: dict, project_path: str, 
                            project_config: dict, gitlab_url_slug: str):
    """处理 MR 评论触发的代码审查"""
    logger.info(f"检测到 MR @机器人触发代码审查，开始处理")
    
    # 获取 MR 的代码变更
    changes = handler.get_merge_request_changes()
    changes = filter_changes(changes, project_config)
    
    if not changes:
        handler.add_merge_request_notes("📝 未检测到需要审查的代码变更（修改文件可能不满足 SUPPORTED_EXTENSIONS 配置）")
        logger.info("未检测到代码变更")
        return
    
    # 统计代码变更量
    additions = sum(item.get('additions', 0) for item in changes)
    deletions = sum(item.get('deletions', 0) for item in changes)
    
    # 获取提交记录
    commits = handler.get_merge_request_commits()
    commits_text = ';'.join(commit.get('title', '') for commit in commits) if commits else ''
    
    # 检查是否启用行级评审
    line_review_enabled = project_config.get('LINE_REVIEW_ENABLED', '0') == '1'
    
    if line_review_enabled:
        # 使用行级审查器
        logger.info("使用行级代码审查模式（MR @触发）")
        line_reviewer = LineReviewer(project_path=project_path, config=project_config)
        line_review_result = line_reviewer.review_and_parse(str(changes), commits_text)
        
        # 获取行级评论
        line_comments = line_review_result.get('line_comments', [])
        
        # 先添加行级评论
        if line_comments:
            success_count = handler.add_line_level_comments(line_comments)
            logger.info(f"成功添加 {success_count} 条行级评论")
        
        # 获取格式化的摘要
        review_result = line_reviewer.get_formatted_summary(line_review_result)
        score = line_review_result.get('score', 0)
    else:
        # 使用传统总结式审查
        logger.info("使用总结式代码审查模式（MR @触发）")
        reviewer = CodeReviewer(project_path=project_path, config=project_config)
        review_result = reviewer.review_and_strip_code(str(changes), commits_text)
        score = CodeReviewer.parse_review_score(review_text=review_result)
    
    # 添加触发信息到评审结果
    trigger_info = f"\n\n---\n*🤖 此评审由 @{webhook_data.get('user', {}).get('username', 'unknown')} 通过评论触发*"
    review_result_with_info = f"Auto Review Result:\n{review_result}{trigger_info}"
    
    # 发布评审结果
    handler.add_merge_request_notes(review_result_with_info)
    
    logger.info(f"MR @触发代码审查完成，评分: {score}")
    
    # 发送 IM 通知（可选）
    _send_mention_notification(webhook_data, project_config, score, additions, deletions, "MR")


def _handle_commit_note_review(handler: NoteHandler, webhook_data: dict, project_path: str,
                                project_config: dict, gitlab_url_slug: str):
    """处理 Commit 评论触发的代码审查"""
    logger.info(f"检测到 Commit @机器人触发代码审查，开始处理")
    
    # 获取 Commit 的代码变更
    changes = handler.get_commit_diff()
    
    # 转换格式以适配 filter_changes
    formatted_changes = []
    for change in changes:
        formatted_changes.append({
            'diff': change.get('diff', ''),
            'new_path': change.get('new_path', ''),
            'old_path': change.get('old_path', ''),
            'deleted_file': change.get('deleted_file', False)
        })
    
    changes = filter_changes(formatted_changes, project_config)
    
    if not changes:
        handler.add_commit_notes("📝 未检测到需要审查的代码变更（修改文件可能不满足 SUPPORTED_EXTENSIONS 配置）")
        logger.info("未检测到代码变更")
        return
    
    # 统计代码变更量
    additions = sum(item.get('additions', 0) for item in changes)
    deletions = sum(item.get('deletions', 0) for item in changes)
    
    # 获取 commit 信息
    commit_info = handler.get_commit_info()
    commits_text = commit_info.get('title', '') or commit_info.get('message', '')
    
    # 使用总结式审查（Commit 不支持行级评论）
    logger.info("使用总结式代码审查模式（Commit @触发）")
    reviewer = CodeReviewer(project_path=project_path, config=project_config)
    review_result = reviewer.review_and_strip_code(str(changes), commits_text)
    score = CodeReviewer.parse_review_score(review_text=review_result)
    
    # 添加触发信息到评审结果
    trigger_info = f"\n\n---\n*🤖 此评审由 @{webhook_data.get('user', {}).get('username', 'unknown')} 通过评论触发*"
    review_result_with_info = f"Auto Review Result:\n{review_result}{trigger_info}"
    
    # 发布评审结果
    handler.add_commit_notes(review_result_with_info)
    
    logger.info(f"Commit @触发代码审查完成，评分: {score}")
    
    # 发送 IM 通知（可选）
    _send_mention_notification(webhook_data, project_config, score, additions, deletions, "Commit")


def _send_mention_notification(webhook_data: dict, project_config: dict, score: int, 
                                additions: int, deletions: int, review_type: str):
    """发送 @触发审查的 IM 通知"""
    notify_enabled = project_config.get('MENTION_TRIGGER_NOTIFY_ENABLED', '0') == '1'
    if notify_enabled:
        notify_msg = f"🤖 代码审查完成（{review_type}）\n项目: {webhook_data.get('project', {}).get('name')}\n触发者: @{webhook_data.get('user', {}).get('username')}\n评分: {score}\n新增: {additions} 行 / 删除: {deletions} 行"
        notifier.send_notification(content=notify_msg, project_config=project_config)


def handle_merge_request_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    '''
    处理Merge Request Hook事件
    :param webhook_data:
    :param gitlab_token:
    :param gitlab_url:
    :param gitlab_url_slug:
    :return:
    '''
    # 初始化project_config为None，确保在异常处理中可以访问
    project_config = None
    try:
        # 提取项目路径
        project_path = webhook_data.get('project', {}).get('path_with_namespace', '')
        logger.info(f'Project path: {project_path}')
        
        # 加载项目专属配置（不修改全局环境变量）
        project_config = config_loader.get_config(project_path=project_path)
        
        # 检查白名单（传递project_config确保配置隔离）
        if not check_project_whitelist(project_path, project_config=project_config):
            logger.info(f'项目 {project_path} 不在白名单中，跳过Merge Request Review')
            return
        logger.info(f'项目 {project_path} 使用独立配置上下文')
        
        # 从项目配置中读取 GITLAB_ACCESS_TOKEN
        gitlab_token = project_config.get('GITLAB_ACCESS_TOKEN') or gitlab_token
        
        # 检查是否仅review protected branches
        merge_review_only_protected_branches = project_config.get('MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED', '0') == '1'
        
        # 解析Webhook数据
        handler = MergeRequestHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Merge Request Hook event received')

        # 检查MR作者是否在排除列表中
        excluded_users = project_config.get('MERGE_REVIEW_EXCLUDED_USERS', 'howbuyscm').split(',')
        excluded_users = [user.strip() for user in excluded_users if user.strip()]
        if handler.is_author_excluded(excluded_users):
            return

        # 新增：判断是否为draft（草稿）MR
        object_attributes = webhook_data.get('object_attributes', {})
        is_draft = object_attributes.get('draft') or object_attributes.get('work_in_progress')
        if is_draft:
            msg = f"[通知] MR为草稿（draft），未触发AI审查。\n项目: {webhook_data['project']['name']}\n作者: {webhook_data['user']['username']}\n源分支: {object_attributes.get('source_branch')}\n目标分支: {object_attributes.get('target_branch')}\n链接: {object_attributes.get('url')}"
            notifier.send_notification(content=msg, project_config=project_config)
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
            
            # 创建ReviewService实例并调用方法
            if ReviewService().check_mr_last_commit_id_exists(project_name, source_branch, target_branch, last_commit_id):
                logger.info(f"Merge Request with last_commit_id {last_commit_id} already exists, skipping review for {project_name}.")
                return

        # 仅仅在MR创建或更新时进行Code Review
        # 获取Merge Request的changes
        changes = handler.get_merge_request_changes()
        logger.info('changes: %s', changes)
        changes = filter_changes(changes, project_config)
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

        # 检查是否启用行级评审
        line_review_enabled = project_config.get('MERGE_REQUEST_LINE_REVIEW_ENABLED', '0') == '1'
        
        # review 代码
        commits_text = ';'.join(commit['title'] for commit in commits)
        
        if line_review_enabled:
            # 使用行级审查器
            logger.info("启用行级代码审查模式")
            line_reviewer = LineReviewer(project_path=project_path, config=project_config)
            line_review_result = line_reviewer.review_and_parse(str(changes), commits_text)
            
            # 获取行级评论
            line_comments = line_review_result.get('line_comments', [])
            
            # 先添加行级评论
            if line_comments:
                success_count = handler.add_line_level_comments(line_comments)
                logger.info(f"成功添加 {success_count} 条行级评论")
            
            # 获取格式化的摘要作为总体评论
            review_result = line_reviewer.get_formatted_summary(line_review_result)
            score = line_review_result.get('score', 0)
            
            # 将摘要作为总体评论提交到Gitlab的 notes
            handler.add_merge_request_notes(f'Auto Review Result: \n{review_result}')
        else:
            # 使用原有的总结式审查
            review_result = CodeReviewer(project_path=project_path, config=project_config).review_and_strip_code(str(changes), commits_text)
            score = CodeReviewer.parse_review_score(review_text=review_result)
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
                project_config=project_config,
            )
        )

    except Exception as e:
        error_message = f'AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        # 尝试获取project_config，如果异常发生在配置加载之前则为None
        try:
            notifier.send_notification(content=error_message, project_config=project_config)
        except NameError:
            notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)

def handle_github_push_event(webhook_data: dict, github_token: str, github_url: str, github_url_slug: str):
    # 初始化project_config为None，确保在异常处理中可以访问
    project_config = None
    try:
        # 提取项目路径
        project_path = webhook_data.get('repository', {}).get('full_name', '')
        logger.info(f'Project path: {project_path}')
        
        # 加载项目专属配置（不修改全局环境变量）
        project_config = config_loader.get_config(project_path=project_path)
        
        # 检查白名单（传递project_config确保配置隔离）
        if not check_project_whitelist(project_path, project_config=project_config):
            logger.info(f'项目 {project_path} 不在白名单中，跳过GitHub Push Review')
            return
        logger.info(f'项目 {project_path} 使用独立配置上下文')
        
        # 从项目配置中读取 GITHUB_ACCESS_TOKEN
        github_token = project_config.get('GITHUB_ACCESS_TOKEN') or github_token
        
        # 检查是否启用Push Review
        push_review_enabled = project_config.get('PUSH_REVIEW_ENABLED', '0') == '1'
        
        handler = GithubPushHandler(webhook_data, github_token, github_url)
        logger.info('GitHub Push event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # 检查是否启用了commit message检查
        commit_message_check_enabled = project_config.get('PUSH_COMMIT_MESSAGE_CHECK_ENABLED', '0') == '1'
        if commit_message_check_enabled:
            # 获取检查规则（支持正则表达式）
            check_pattern = project_config.get('PUSH_COMMIT_MESSAGE_CHECK_PATTERN', 'review')
            try:
                # 检查所有commits的message是否匹配正则表达式
                pattern = re.compile(check_pattern, re.IGNORECASE)
                has_match = any(pattern.search(commit.get('message', '')) for commit in commits)
                if not has_match:
                    logger.info(f'Commits message中未匹配到指定规则 "{check_pattern}"，跳过本次审查。')
                    return
                logger.info(f'Commits message匹配规则 "{check_pattern}"，继续执行审查。')
            except re.error as e:
                logger.error(f'正则表达式 "{check_pattern}" 格式错误: {e}，跳过检查继续执行。')

        review_result = ""
        score = 0
        additions = 0
        deletions = 0
        note_url = ''  # 存储AI Review结果的URL
        if push_review_enabled:
            # 获取PUSH的changes
            changes = handler.get_push_changes()
            logger.info('changes: %s', changes)
            changes = filter_github_changes(changes, project_config)
            if not changes:
                logger.info('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            review_result = "关注的文件没有修改"

            if len(changes) > 0:
                commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                review_result = CodeReviewer(project_path=project_path, config=project_config).review_and_strip_code(str(changes), commits_text)
                score = CodeReviewer.parse_review_score(review_text=review_result)
                for item in changes:
                    additions += item.get('additions', 0)
                    deletions += item.get('deletions', 0)
            # 将review结果提交到GitHub的 notes
            note_url = handler.add_push_notes(f'Auto Review Result: \n{review_result}')

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
            note_url=note_url,
            project_config=project_config,
        ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        # 尝试获取project_config，如果异常发生在配置加载之前则为None
        try:
            notifier.send_notification(content=error_message, project_config=project_config)
        except NameError:
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
    # 初始化project_config为None，确保在异常处理中可以访问
    project_config = None
    try:
        # 提取项目路径
        project_path = webhook_data.get('repository', {}).get('full_name', '')
        logger.info(f'Project path: {project_path}')
        
        # 加载项目专属配置（不修改全局环境变量）
        project_config = config_loader.get_config(project_path=project_path)
        
        # 检查白名单（传递project_config确保配置隔离）
        if not check_project_whitelist(project_path, project_config=project_config):
            logger.info(f'项目 {project_path} 不在白名单中，跳过GitHub Pull Request Review')
            return
        logger.info(f'项目 {project_path} 使用独立配置上下文')
        
        # 从项目配置中读取 GITHUB_ACCESS_TOKEN
        github_token = project_config.get('GITHUB_ACCESS_TOKEN') or github_token
        
        # 检查是否仅review protected branches
        merge_review_only_protected_branches = project_config.get('MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED', '0') == '1'
        
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
            
            # 创建ReviewService实例并调用方法
            if ReviewService().check_mr_last_commit_id_exists(project_name, source_branch, target_branch, github_last_commit_id):
                logger.info(f"Pull Request with last_commit_id {github_last_commit_id} already exists, skipping review for {project_name}.")
                return

        # 仅仅在PR创建或更新时进行Code Review
        # 获取Pull Request的changes
        changes = handler.get_pull_request_changes()
        logger.info('changes: %s', changes)
        changes = filter_github_changes(changes, project_config)
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
        commits_text = ';'.join(commit['title'] for commit in commits)
        review_result = CodeReviewer(project_path=project_path, config=project_config).review_and_strip_code(str(changes), commits_text)

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
                project_config=project_config,
            ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        # 尝试获取project_config，如果异常发生在配置加载之前则为None
        try:
            notifier.send_notification(content=error_message, project_config=project_config)
        except NameError:
            notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_gitea_push_event(webhook_data: dict, gitea_token: str, gitea_url: str, gitea_url_slug: str):
    # 初始化project_config为None，确保在异常处理中可以访问
    project_config = None
    try:
        # 提取项目路径
        repository = webhook_data.get('repository', {})
        project_path = repository.get('full_name', '')
        logger.info(f'Project path: {project_path}')

        # 加载项目专属配置（不修改全局环境变量）
        project_config = config_loader.get_config(project_path=project_path)

        # 检查白名单（传递project_config确保配置隔离）
        if not check_project_whitelist(project_path, project_config=project_config):
            logger.info(f'项目 {project_path} 不在白名单中，跳过Gitea Push Review')
            return
        logger.info(f'项目 {project_path} 使用独立配置上下文')

        # 从项目配置中读取 GITEA_ACCESS_TOKEN
        gitea_token = project_config.get('GITEA_ACCESS_TOKEN') or gitea_token

        # 检查是否启用Push Review
        push_review_enabled = project_config.get('PUSH_REVIEW_ENABLED', '0') == '1'

        handler = GiteaPushHandler(webhook_data, gitea_token, gitea_url)
        logger.info('Gitea Push event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # 检查是否启用了commit message检查
        commit_message_check_enabled = project_config.get('PUSH_COMMIT_MESSAGE_CHECK_ENABLED', '0') == '1'
        if commit_message_check_enabled:
            # 获取检查规则（支持正则表达式）
            check_pattern = project_config.get('PUSH_COMMIT_MESSAGE_CHECK_PATTERN', 'review')
            try:
                # 检查所有commits的message是否匹配正则表达式
                pattern = re.compile(check_pattern, re.IGNORECASE)
                has_match = any(pattern.search(commit.get('message', '')) for commit in commits)
                if not has_match:
                    logger.info(f'Commits message中未匹配到指定规则 "{check_pattern}"，跳过本次审查。')
                    return
                logger.info(f'Commits message匹配规则 "{check_pattern}"，继续执行审查。')
            except re.error as e:
                logger.error(f'正则表达式 "{check_pattern}" 格式错误: {e}，跳过检查继续执行。')

        review_result = ""
        score = 0
        additions = 0
        deletions = 0
        note_url = ''  # 存储AI Review结果的URL
        if push_review_enabled:
            changes = handler.get_push_changes()
            logger.info('changes: %s', changes)
            changes = filter_gitea_changes(changes, project_config)
            if not changes:
                logger.info('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            review_result = "关注的文件没有修改"

            if len(changes) > 0:
                commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                review_result = CodeReviewer(project_path=project_path, config=project_config).review_and_strip_code(str(changes), commits_text)
                score = CodeReviewer.parse_review_score(review_text=review_result)
                for item in changes:
                    additions += item.get('additions', 0)
                    deletions += item.get('deletions', 0)
            note_url = handler.add_push_notes(f'Auto Review Result: \n{review_result}')

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
            note_url=note_url,
            project_config=project_config,
        ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        # 尝试获取project_config，如果异常发生在配置加载之前则为None
        try:
            notifier.send_notification(content=error_message, project_config=project_config)
        except NameError:
            notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_gitea_pull_request_event(webhook_data: dict, gitea_token: str, gitea_url: str, gitea_url_slug: str):
    # 初始化project_config为None，确保在异常处理中可以访问
    project_config = None
    try:
        # 提取项目路径
        repository = webhook_data.get('repository', {})
        project_path = repository.get('full_name', '')
        logger.info(f'Project path: {project_path}')

        # 加载项目专属配置（不修改全局环境变量）
        project_config = config_loader.get_config(project_path=project_path)

        # 检查白名单（传递project_config确保配置隔离）
        if not check_project_whitelist(project_path, project_config=project_config):
            logger.info(f'项目 {project_path} 不在白名单中，跳过Gitea Pull Request Review')
            return
        logger.info(f'项目 {project_path} 使用独立配置上下文')

        # 从项目配置中读取 GITEA_ACCESS_TOKEN
        gitea_token = project_config.get('GITEA_ACCESS_TOKEN') or gitea_token

        # 检查是否仅review protected branches
        merge_review_only_protected_branches = project_config.get('MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED', '0') == '1'

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
        changes = filter_gitea_changes(changes, project_config)
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

        commits_text = ';'.join(commit.get('title', '') for commit in commits)
        review_result = CodeReviewer(project_path=project_path, config=project_config).review_and_strip_code(str(changes), commits_text)

        handler.add_pull_request_notes(f'Auto Review Result: \n{review_result}')

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
                project_config=project_config,
            ))

    except Exception as e:
        error_message = f'AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        # 尝试获取project_config，如果异常发生在配置加载之前则为None
        try:
            notifier.send_notification(content=error_message, project_config=project_config)
        except NameError:
            notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)
