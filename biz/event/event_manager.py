from blinker import Signal

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.service.review_service import ReviewService
from biz.utils.im import notifier

from biz.utils.i18n import get_translator
_ = get_translator()

# 定义全局事件管理器（事件信号）
event_manager = {
    "merge_request_reviewed": Signal(),
    "push_reviewed": Signal(),
}


# 定义事件处理函数
def on_merge_request_reviewed(mr_review_entity: MergeRequestReviewEntity):
    # 发送IM消息通知
    im_msg = _("""
### 🔀 {project_name}: Merge Request

#### 合并请求信息:
- **提交者:** {author}

- **源分支**: {source_branch}
- **目标分支**: {target_branch}
- **更新时间**: {updated_at}
- **提交信息:** {commit_messages}

- [查看合并详情]({url})

- **AI Review 结果:** 

{review_result}
    """).format(
        project_name=mr_review_entity.project_name,
        author=mr_review_entity.author,
        source_branch=mr_review_entity.source_branch,
        target_branch=mr_review_entity.target_branch,
        updated_at=mr_review_entity.updated_at,
        commit_messages=mr_review_entity.commit_messages,
        url=mr_review_entity.url,
        review_result=mr_review_entity.review_result
    )
    notifier.send_notification(content=im_msg, msg_type='markdown', title=_('Merge Request Review'),
                                  project_name=mr_review_entity.project_name,
                                  url_slug=mr_review_entity.url_slug)

    # 记录到数据库
    ReviewService().insert_mr_review_log(mr_review_entity)


def on_push_reviewed(entity: PushReviewEntity):
    # 发送IM消息通知
    im_msg = _("### 🚀 {project_name}: Push\n\n").format(project_name=entity.project_name)
    im_msg += _("#### 提交记录:\n")

    for commit in entity.commits:
        message = commit.get('message', '').strip()
        author = commit.get('author', _('Unknown Author'))
        timestamp = commit.get('timestamp', '')
        url = commit.get('url', '#')
        im_msg += (
            _("- **提交信息**: {message}\n"
              "- **提交者**: {author}\n"
              "- **时间**: {timestamp}\n"
              "- [查看提交详情]({url})\n\n").format(
                message=message,
                author=author,
                timestamp=timestamp,
                url=url
            )
        )

    if entity.review_result:
        im_msg += _("#### AI Review 结果: \n {review_result}\n\n").format(review_result=entity.review_result)
    notifier.send_notification(content=im_msg, msg_type='markdown',
                               title=_("{project_name} Push Event").format(project_name=entity.project_name),
                               project_name=entity.project_name,
                               url_slug=entity.url_slug)

    # 记录到数据库
    ReviewService().insert_push_review_log(entity)


# 连接事件处理函数到事件信号
event_manager["merge_request_reviewed"].connect(on_merge_request_reviewed)
event_manager["push_reviewed"].connect(on_push_reviewed)