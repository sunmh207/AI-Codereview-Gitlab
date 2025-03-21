import os
import traceback
from datetime import datetime

from dotenv import load_dotenv

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.event.event_manager import event_manager
from biz.gitlab.webhook_handler import filter_changes, MergeRequestHandler, PushHandler, slugify_url
from biz.utils.code_reviewer import CodeReviewer
from biz.utils.im import im_notifier
from biz.utils.log import logger

load_dotenv()
PUSH_REVIEW_ENABLED = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'

from biz.utils.i18n import get_translator
_ = get_translator()

def handle_push_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    try:
        handler = PushHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Push Hook event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error(_('Failed to get commits'))
            return

        review_result = None
        score = 0
        if PUSH_REVIEW_ENABLED:
            # 获取PUSH的changes
            changes = handler.get_push_changes()
            logger.info('changes: %s', changes)
            changes = filter_changes(changes)
            if not changes:
                logger.info(_('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。'))
            review_result = _("关注的文件没有修改")

            if len(changes) > 0:
                commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)
                score = CodeReviewer.parse_review_score(review_text=review_result)
            # 将review结果提交到Gitlab的 notes
            handler.add_push_notes(_('Auto Review Result: \n{}').format(review_result))

        # TODO check if not also queueing makes sense here
        event_manager['push_reviewed'].send(PushReviewEntity(
            project_name=webhook_data['project']['name'],
            author=webhook_data['user_username'],
            branch=webhook_data['project']['default_branch'],
            updated_at=int(datetime.now().timestamp()),  # 当前时间
            commits=commits,
            score=score,
            review_result=review_result,
            gitlab_url_slug=gitlab_url_slug
        ))

    except Exception as e:
        error_message = _('服务出现未知错误: {}').format(f'{str(e)}\n{traceback.format_exc()}')
        im_notifier.send_notification(content=error_message)
        logger.error(_('出现未知错误: {}').format(error_message))


def handle_merge_request_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    '''
    处理Merge Request Hook事件
    :param webhook_data:
    :param gitlab_token:
    :param gitlab_url:
    :param gitlab_url_slug:
    :return:
    '''
    try:
        # 解析Webhook数据
        handler = MergeRequestHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info(_('Merge Request Hook event received'))

        if handler.action in ['open', 'update']:  # 仅仅在MR创建或更新时进行Code Review
            # 获取Merge Request的changes
            changes = handler.get_merge_request_changes()
            logger.info(_('changes: {}').format(changes))
            changes = filter_changes(changes)
            if not changes:
                logger.info(_('未检测到有关代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。'))
                return

            # 获取Merge Request的commits
            commits = handler.get_merge_request_commits()
            if not commits:
                logger.error(_('Failed to get commits'))
                return

            # review 代码
            commits_text = ';'.join(commit['title'] for commit in commits)
            review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)

            # 将review结果提交到Gitlab的 notes
            handler.add_merge_request_notes(_('Auto Review Result: \n{}').format(review_result))

            # dispatch merge_request_reviewed event
            # TODO check if not also queueing makes sense here
            # dispatch merge_request_reviewed event
            event_manager['merge_request_reviewed'].send(
                MergeRequestReviewEntity(
                    project_name=webhook_data['project']['name'],
                    author=webhook_data['user']['username'],
                    source_branch=webhook_data['object_attributes']['source_branch'],
                    target_branch=webhook_data['object_attributes']['target_branch'],
                    updated_at=int(datetime.now().timestamp()),
                    commits=commits,
                    score=CodeReviewer.parse_review_score(review_text=review_result),
                    url=webhook_data['object_attributes']['url'],
                    review_result=review_result,
                    gitlab_url_slug= gitlab_url_slug,
                )
            )

        else:
            logger.info(_("Merge Request Hook event, action={}, ignored.").format(handler.action))

    except Exception as e:
        error_message = _('AI Code Review 服务出现未知错误: {}').format(f'{str(e)}\n{traceback.format_exc()}')
        im_notifier.send_notification(content=error_message)
        logger.error(_('出现未知错误: {}').format(error_message))
