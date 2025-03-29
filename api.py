import atexit
import json
import os
import traceback
from datetime import datetime
from urllib.parse import urlparse

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from flask import Flask, request, jsonify

from biz.gitlab.webhook_handler import slugify_url
from biz.queue.worker import handle_merge_request_event, handle_push_event, handle_github_pull_request_event, handle_github_push_event
from biz.service.review_service import ReviewService
from biz.utils.config_checker import check_config
from biz.utils.im import notifier
from biz.utils.log import logger
from biz.utils.queue import handle_queue
from biz.utils.reporter import Reporter

load_dotenv("conf/.env")
api_app = Flask(__name__)

from biz.utils.i18n import get_translator

_ = get_translator()

PUSH_REVIEW_ENABLED = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'


@api_app.route('/')
def home():
    return """<h2>The code review api server is running.</h2>
              <p>GitHub project address: <a href="https://github.com/mashb1t/ai-codereview-gitlab" target="_blank">
              https://github.com/mashb1t/ai-codereview-gitlab</a></p>
              """


@api_app.route('/review/daily_report', methods=['GET'])
def daily_report():
    # 获取当前日期0点和23点59分59秒的时间戳
    start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    end_time = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).timestamp()

    # import translator once more due to separate cronjob process
    from biz.utils.i18n import get_translator
    _ = get_translator()

    try:
        if PUSH_REVIEW_ENABLED:
            df = ReviewService().get_push_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)
        else:
            df = ReviewService().get_mr_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)

        if df.empty:
            logger.info(_("No data to process."))
            return jsonify({'message': _('No data to process.')}), 200
        # 去重：基于 (author, message) 组合
        df_unique = df.drop_duplicates(subset=["author", "commit_messages"])
        # 按照 author 排序
        df_sorted = df_unique.sort_values(by="author")
        # 转换为适合生成日报的格式
        commits = df_sorted.to_dict(orient="records")
        # 生成日报内容
        report_txt = Reporter().generate_report(json.dumps(commits))
        # 发送钉钉通知
        notifier.send_notification(content=report_txt, msg_type="markdown", title=_("代码提交日报"))

        # 返回生成的日报内容
        return json.dumps(report_txt, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(_("Failed to generate daily report: {}").format(e))
        return jsonify({'message': f"Failed to generate daily report: {e}"}), 500


def setup_scheduler():
    """
    配置并启动定时任务调度器
    """
    try:
        scheduler = BackgroundScheduler()
        crontab_expression = os.getenv('REPORT_CRONTAB_EXPRESSION', '0 18 * * 1-5')
        cron_parts = crontab_expression.split()
        cron_minute, cron_hour, cron_day, cron_month, cron_day_of_week = cron_parts

        # Schedule the task based on the crontab expression
        scheduler.add_job(
            daily_report,
            trigger=CronTrigger(
                minute=cron_minute,
                hour=cron_hour,
                day=cron_day,
                month=cron_month,
                day_of_week=cron_day_of_week
            )
        )

        # Start the scheduler
        scheduler.start()
        logger.info(_("Scheduler started successfully."))

        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())
    except Exception as e:
        logger.error(_("Error setting up scheduler: {}").format(e))
        logger.error(traceback.format_exc())


# 处理 GitLab Merge Request Webhook
@api_app.route('/review/webhook', methods=['POST'])
def handle_webhook():
    # 获取请求的JSON数据
    if request.is_json:
        data = request.get_json()
        if not data:
            return jsonify({"error": _("Invalid JSON")}), 400

        # 判断是GitLab还是GitHub的webhook
        webhook_source = request.headers.get('X-GitHub-Event')

        if webhook_source:  # GitHub webhook
            return handle_github_webhook(webhook_source, data)
        else:  # GitLab webhook
            return handle_gitlab_webhook(data)
    else:
        return jsonify({'message': _('Invalid data format')}), 400


def handle_github_webhook(event_type, data):
    # 获取GitHub配置
    github_token = os.getenv('GITHUB_ACCESS_TOKEN') or request.headers.get('X-GitHub-Token')
    if not github_token:
        return jsonify({'message': _('Missing GitLab URL')}), 400

    github_url = os.getenv('GITHUB_URL') or 'https://github.com'
    github_url_slug = slugify_url(github_url)

    # 打印整个payload数据
    logger.info(_('Received event: {}').format(event_type))
    logger.info(_('Payload: {}').format(json.dumps(data)))

    if event_type == "pull_request":
        # 使用handle_queue进行异步处理
        handle_queue(handle_github_pull_request_event, data, github_token, github_url, github_url_slug)
        # 立马返回响应
        return jsonify({'message': _('GitHub request received(event_type={}), will process asynchronously.').format(
            event_type)}), 200
    elif event_type == "push":
        # 使用handle_queue进行异步处理
        handle_queue(handle_github_push_event, data, github_token, github_url, github_url_slug)
        # 立马返回响应
        return jsonify({'message': _('GitHub request received(event_type={}), will process asynchronously.').format(
            event_type)}), 200
    else:
        error_message = _(
            'Only pull_request and push events are supported for GitHub webhook, but received:: {}.').format(
            event_type)
        logger.error(error_message)
        return jsonify(error_message), 400


def handle_gitlab_webhook(data):
    object_kind = data.get("object_kind")

    # 优先从请求头获取，如果没有，则从环境变量获取，如果没有，则从推送事件中获取
    gitlab_url = os.getenv('GITLAB_URL') or request.headers.get('X-Gitlab-Instance')
    if not gitlab_url:
        repository = data.get('repository')
        if not repository:
            return jsonify({'message': _('Missing GitLab URL')}), 400
        homepage = repository.get("homepage")
        if not homepage:
            return jsonify({'message': _('Missing GitLab URL')}), 400
        try:
            parsed_url = urlparse(homepage)
            gitlab_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        except Exception as e:
            return jsonify({"error": _("Failed to parse homepage URL: {}").format(str(e))}), 400

    # 优先从环境变量获取，如果没有，则从请求头获取
    gitlab_token = os.getenv('GITLAB_ACCESS_TOKEN') or request.headers.get('X-Gitlab-Token')
    # 如果gitlab_token为空，返回错误
    if not gitlab_token:
        return jsonify({'message': _('Missing GitLab access token')}), 400

    gitlab_url_slug = slugify_url(gitlab_url)

    # 打印整个payload数据，或根据需求进行处理
    logger.info(_('Received event: {}').format(object_kind))
    logger.info(_('Payload: {}').format(json.dumps(data)))

    # 处理Merge Request Hook
    if object_kind == "merge_request":
        # 创建一个新进程进行异步处理
        handle_queue(handle_merge_request_event, data, gitlab_token, gitlab_url, gitlab_url_slug)
        # 立马返回响应
        return jsonify({'message': _('Request received(object_kind={}), will process asynchronously.').format(
            object_kind)}), 200
    elif object_kind == "push":
        # 创建一个新进程进行异步处理
        # TODO check if PUSH_REVIEW_ENABLED is needed here
        handle_queue(handle_push_event, data, gitlab_token, gitlab_url, gitlab_url_slug)
        # 立马返回响应
        return jsonify({'message': _('Request received(object_kind={}), will process asynchronously.').format(
            object_kind)}), 200
    else:
        error_message = _(
            'Only merge_request and push events are supported (both Webhook and System Hook), but received: {}.').format(
            object_kind)
        logger.error(error_message)
        return jsonify(error_message), 400


if __name__ == '__main__':
    check_config()
    # 启动定时任务调度器
    setup_scheduler()

    # 启动Flask API服务
    port = int(os.environ.get('SERVER_PORT', 5001))
    api_app.run(host='0.0.0.0', port=port)
