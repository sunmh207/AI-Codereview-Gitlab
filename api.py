from dotenv import load_dotenv

load_dotenv("conf/.env")

import atexit
import json
import os
import traceback
from datetime import datetime
from urllib.parse import urlparse

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, request, jsonify

from biz.gitlab.webhook_handler import slugify_url
from biz.queue.worker import handle_merge_request_event, handle_push_event, handle_github_pull_request_event, \
    handle_github_push_event, handle_gitea_pull_request_event, handle_gitea_push_event, handle_note_event
from biz.service.review_service import ReviewService
from biz.utils.im import notifier
from biz.utils.log import logger
from biz.utils.queue import handle_queue
from biz.utils.reporter import Reporter

from biz.utils.config_checker import check_config

api_app = Flask(__name__)

push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'


@api_app.route('/')
def home():
    return """<h2>The code review api server is running.</h2>
              <p>GitHub project address: <a href="https://github.com/sunmh207/AI-Codereview-Gitlab" target="_blank">
              https://github.com/sunmh207/AI-Codereview-Gitlab</a></p>
              <p>Gitee project address: <a href="https://gitee.com/sunminghui/ai-codereview-gitlab" target="_blank">https://gitee.com/sunminghui/ai-codereview-gitlab</a></p>
              """


def generate_daily_report_core():
    """
    日报生成核心逻辑，供Flask路由和定时任务共同调用
    :return: (report_text, error_message)
    """
    logger.info("开始生成日报...")
    
    # 获取当前日期0点和23点59分59秒的时间戳
    start_time = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    end_time = int(datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).timestamp())
    
    logger.info(f"查询时间范围: {start_time} - {end_time}")

    try:
        if push_review_enabled:
            logger.info("PUSH_REVIEW_ENABLED=true, 获取push review日志")
            df = ReviewService().get_push_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)
        else:
            logger.info("PUSH_REVIEW_ENABLED=false, 获取merge request review日志")
            df = ReviewService().get_mr_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)

        if df.empty:
            logger.info("没有找到相关数据.")
            return None, "No data to process."
        
        logger.info(f"获取到 {len(df)} 条原始记录")
        
        # 去重：基于 (author, message) 组合
        df_unique = df.drop_duplicates(subset=["author", "commit_messages"])
        logger.info(f"去重后剩余 {len(df_unique)} 条记录")
        
        # 按照 author 排序
        df_sorted = df_unique.sort_values(by="author")
        logger.info("数据已按作者排序")
        
        # 转换为适合生成日报的格式
        commits = df_sorted.to_dict(orient="records")
        logger.info(f"转换为 {len(commits)} 条提交记录用于日报生成")
        
        # 生成日报内容(Reporter会从环境变量读取LLM配置)
        logger.info("开始调用LLM生成日报内容...")
        report_txt = Reporter().generate_report(json.dumps(commits))
        logger.info("LLM日报内容生成完成")
        
        # 发送IM通知，使用 msg_category='daily_report' 来使用独立的日报webhook
        logger.info("开始发送IM通知...")
        notifier.send_notification(
            content=report_txt, 
            msg_type="markdown", 
            title="代码提交日报",
            msg_category="daily_report",
            project_config=None  # 日报是全局任务,使用默认配置
        )
        logger.info("IM通知发送完成")

        return report_txt, None
    except Exception as e:
        logger.error(f"❌ Failed to generate daily report: {e}", exc_info=True)
        return None, str(e)


@api_app.route('/review/daily_report', methods=['GET'])
def daily_report():
    """
    日报生成Flask路由接口
    """
    report_txt, error = generate_daily_report_core()
    
    if error:
        return jsonify({'message': error}), 500 if report_txt is None else 200
    
    # 返回生成的日报内容
    return json.dumps(report_txt, ensure_ascii=False, indent=4)


def daily_report_scheduled():
    """
    定时任务专用的日报生成函数（不依赖Flask应用上下文）
    """
    logger.info("⏰ Scheduled daily report task started...")
    report_txt, error = generate_daily_report_core()
    
    if error and report_txt is None:
        logger.error(f"❌ Scheduled daily report failed: {error}")
    else:
        logger.info("✅ Scheduled daily report generated successfully")


def setup_scheduler():
    """
    配置并启动定时任务调度器
    """
    try:
        scheduler = BackgroundScheduler()
        crontab_expression = os.getenv('REPORT_CRONTAB_EXPRESSION', '0 18 * * 1-5')
        cron_parts = crontab_expression.split()
        cron_minute, cron_hour, cron_day, cron_month, cron_day_of_week = cron_parts

        logger.info(f"Configuring scheduler with cron expression: {crontab_expression}")
        logger.info(f"Parsed cron: minute={cron_minute}, hour={cron_hour}, day={cron_day}, month={cron_month}, day_of_week={cron_day_of_week}")

        # Schedule the task based on the crontab expression
        # 使用 daily_report_scheduled 而不是 daily_report，避免在定时任务中调用Flask路由
        job = scheduler.add_job(
            daily_report_scheduled,
            trigger=CronTrigger(
                minute=cron_minute,
                hour=cron_hour,
                day=cron_day,
                month=cron_month,
                day_of_week=cron_day_of_week
            ),
            id='daily_report_job'
        )

        # Start the scheduler
        scheduler.start()
        logger.info("Scheduler started successfully.")
        
        # Log next run time
        next_run = job.next_run_time
        if next_run:
            logger.info(f"Next scheduled run time: {next_run}")
        else:
            logger.warning("Could not determine next run time for the scheduled job")

        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())
    except Exception as e:
        logger.error(f"Error setting up scheduler: {e}")
        logger.error(traceback.format_exc())


# 处理 GitLab Merge Request Webhook
@api_app.route('/review/webhook', methods=['POST'])
def handle_webhook():
    # 获取请求的JSON数据
    if request.is_json:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        # 判断webhook来源
        webhook_source_github = request.headers.get('X-GitHub-Event')
        webhook_source_gitea = request.headers.get('X-Gitea-Event')

        if webhook_source_gitea:  # Gitea webhook优先处理
            return handle_gitea_webhook(webhook_source_gitea, data)
        elif webhook_source_github:  # GitHub webhook
            return handle_github_webhook(webhook_source_github, data)
        else:  # GitLab webhook
            return handle_gitlab_webhook(data)
    else:
        return jsonify({'message': 'Invalid data format'}), 400


def handle_github_webhook(event_type, data):
    # 获取GitHub配置
    github_token = os.getenv('GITHUB_ACCESS_TOKEN') or request.headers.get('X-GitHub-Token')
    if not github_token:
        return jsonify({'message': 'Missing GitHub access token'}), 400

    github_url = os.getenv('GITHUB_URL') or 'https://github.com'
    github_url_slug = slugify_url(github_url)

    # 打印整个payload数据
    logger.info(f'Received GitHub event: {event_type}')
    logger.info(f'Payload: {json.dumps(data)}')

    if event_type == "pull_request":
        # 使用handle_queue进行异步处理
        handle_queue(handle_github_pull_request_event, data, github_token, github_url, github_url_slug)
        # 立马返回响应
        return jsonify(
            {'message': f'GitHub request received(event_type={event_type}), will process asynchronously.'}), 200
    elif event_type == "push":
        # 使用handle_queue进行异步处理
        handle_queue(handle_github_push_event, data, github_token, github_url, github_url_slug)
        # 立马返回响应
        return jsonify(
            {'message': f'GitHub request received(event_type={event_type}), will process asynchronously.'}), 200
    else:
        error_message = f'Only pull_request and push events are supported for GitHub webhook, but received: {event_type}.'
        logger.error(error_message)
        return jsonify(error_message), 400


def handle_gitlab_webhook(data):
    object_kind = data.get("object_kind")

    # 优先从请求头获取，如果没有，则从环境变量获取，如果没有，则从推送事件中获取
    gitlab_url = os.getenv('GITLAB_URL') or request.headers.get('X-Gitlab-Instance')
    if not gitlab_url:
        repository = data.get('repository')
        if not repository:
            return jsonify({'message': 'Missing GitLab URL'}), 400
        homepage = repository.get("homepage")
        if not homepage:
            return jsonify({'message': 'Missing GitLab URL'}), 400
        try:
            parsed_url = urlparse(homepage)
            gitlab_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        except Exception as e:
            return jsonify({"error": f"Failed to parse homepage URL: {str(e)}"}), 400

    # 优先从环境变量获取，如果没有，则从请求头获取
    gitlab_token = os.getenv('GITLAB_ACCESS_TOKEN') or request.headers.get('X-Gitlab-Token')
    # 如果gitlab_token为空，返回错误
    if not gitlab_token:
        return jsonify({'message': 'Missing GitLab access token'}), 400

    gitlab_url_slug = slugify_url(gitlab_url)

    # 打印整个payload数据，或根据需求进行处理
    logger.info(f'Received event: {object_kind}')
    logger.info(f'Payload: {json.dumps(data)}')

    # 处理Merge Request Hook
    if object_kind == "merge_request":
        # 创建一个新进程进行异步处理
        handle_queue(handle_merge_request_event, data, gitlab_token, gitlab_url, gitlab_url_slug)
        # 立马返回响应
        return jsonify(
            {'message': f'Request received(object_kind={object_kind}), will process asynchronously.'}), 200
    elif object_kind == "push":
        # 创建一个新进程进行异步处理
        # TODO check if PUSH_REVIEW_ENABLED is needed here
        handle_queue(handle_push_event, data, gitlab_token, gitlab_url, gitlab_url_slug)
        # 立马返回响应
        return jsonify(
            {'message': f'Request received(object_kind={object_kind}), will process asynchronously.'}), 200
    elif object_kind == "note":
        # 处理 Note Hook 事件（@机器人触发审查）
        handle_queue(handle_note_event, data, gitlab_token, gitlab_url, gitlab_url_slug)
        return jsonify(
            {'message': f'Request received(object_kind={object_kind}), will process asynchronously.'}), 200
    else:
        error_message = f'Only merge_request, push and note events are supported (both Webhook and System Hook), but received: {object_kind}.'
        logger.error(error_message)
        return jsonify(error_message), 400


def handle_gitea_webhook(event_type, data):
    gitea_token = os.getenv('GITEA_ACCESS_TOKEN') or request.headers.get('X-Gitea-Token')
    if not gitea_token:
        return jsonify({'message': 'Missing Gitea access token'}), 400

    gitea_url = os.getenv('GITEA_URL') or 'https://gitea.com'
    gitea_url_slug = slugify_url(gitea_url)

    logger.info(f'Received Gitea event: {event_type}')
    logger.info(f'Payload: {json.dumps(data)}')

    if event_type == "pull_request":
        handle_queue(handle_gitea_pull_request_event, data, gitea_token, gitea_url, gitea_url_slug)
        return jsonify(
            {'message': f'Gitea request received(event_type={event_type}), will process asynchronously.'}), 200
    elif event_type == "push":
        handle_queue(handle_gitea_push_event, data, gitea_token, gitea_url, gitea_url_slug)
        return jsonify(
            {'message': f'Gitea request received(event_type={event_type}), will process asynchronously.'}), 200
    else:
        error_message = f'Only pull_request and push events are supported for Gitea webhook, but received: {event_type}.'
        logger.error(error_message)
        return jsonify(error_message), 400


if __name__ == '__main__':
    check_config()
    # 启动定时任务调度器
    setup_scheduler()

    # 启动Flask API服务
    port = int(os.environ.get('SERVER_PORT', 5001))
    # 使用 use_reloader=False 避免在开发模式下调度器被初始化两次
    api_app.run(host='0.0.0.0', port=port, use_reloader=False)
