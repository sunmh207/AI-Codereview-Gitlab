from dotenv import load_dotenv

load_dotenv("conf/.env")

import atexit
import json
import os
import traceback
from datetime import datetime, timedelta
from urllib.parse import urlparse

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, request, jsonify

from biz.gitlab.webhook_handler import slugify_url
from biz.queue.worker import handle_merge_request_event, handle_push_event, handle_github_pull_request_event, \
    handle_github_push_event
from biz.service.review_service import ReviewService
from biz.utils.log import logger
from biz.utils.queue import handle_queue
from biz.utils.daily_report_service import DailyReportService

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


@api_app.route('/review/daily_report', methods=['GET'])
def daily_report():
    # 获取当前日期0点和23点59分59秒的时间戳
    start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    end_time = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).timestamp()

    try:
        if push_review_enabled:
            df = ReviewService().get_push_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)
        else:
            df = ReviewService().get_mr_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)

        if df.empty:
            logger.info("No data to process.")
            return jsonify({'message': 'No data to process.'}), 200
        # 去重：基于 (author, message) 组合
        df_unique = df.drop_duplicates(subset=["author", "commit_messages"])
        # 按照 author 排序
        df_sorted = df_unique.sort_values(by="author")
        # 转换为适合生成日报的格式
        commits = df_sorted.to_dict(orient="records")

        # 使用优化后的日报服务 - 每个人生成自己的日报
        daily_report_service = DailyReportService()
        results = daily_report_service.generate_and_send_individual_reports(commits)

        # 记录处理结果
        logger.info(f"总用户: {results['total_users']}, 生成报告: {results['reports_generated']}")

        if results['errors']:
            logger.warning(f"处理过程中的错误: {results['errors'][:5]}")  # 只记录前5个错误

        # 生成汇总报告
        combined_report = daily_report_service.generate_summary_report(results.get('individual_results', []))

        # 发送钉钉通知（汇总报告）
        # notifier.send_notification(content=combined_report, msg_type="markdown", title="代码提交日报")

        # 返回生成的日报内容
        return json.dumps(combined_report, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        return jsonify({'message': f"Failed to generate daily report: {e}"}), 500


@api_app.route('/review/users_without_review', methods=['GET'])
def users_without_review():
    """获取没有代码审查记录的人员列表

    查询参数:
    - time_range: 时间范围，可选值：
      - 'all': 历史所有记录（默认）
      - 'today': 当天
      - 'week': 近一周
    - start_time: 自定义开始时间戳（可选，优先级高于time_range）
    - end_time: 自定义结束时间戳（可选，与start_time配合使用）
    """
    try:
        # 获取查询参数
        time_range = request.args.get('time_range', 'all').lower()
        custom_start_time = request.args.get('start_time')
        custom_end_time = request.args.get('end_time')

        # 计算时间范围
        start_time = None
        end_time = None
        time_description = "历史所有"

        if custom_start_time and custom_end_time:
            # 使用自定义时间范围
            try:
                start_time = int(custom_start_time)
                end_time = int(custom_end_time)
                time_description = f"自定义时间范围 ({datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')} 至 {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')})"
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': '时间戳格式错误，请使用Unix时间戳',
                    'data': {}
                }), 400
        elif time_range == 'today':
            # 当天：从今天0点到23:59:59
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = int(today.timestamp())
            end_time = int(today.replace(hour=23, minute=59, second=59).timestamp())
            time_description = "当天"
        elif time_range == 'week':
            # 近一周：从7天前0点到现在
            week_ago = datetime.now() - timedelta(days=7)
            start_time = int(week_ago.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
            end_time = int(datetime.now().timestamp())
            time_description = "近一周"
        elif time_range != 'all':
            return jsonify({
                'success': False,
                'message': 'time_range 参数无效，支持的值：all, today, week',
                'data': {}
            }), 400

        # 获取指定时间范围内有代码审查记录的作者列表
        reviewed_authors = ReviewService.get_push_review_authors_by_time(
            updated_at_gte=start_time,
            updated_at_lte=end_time
        )
        logger.info(f"Found {len(reviewed_authors)} authors with review records in {time_description}: {reviewed_authors}")

        # 读取飞书用户数据
        feishu_users_file = "biz/utils/im/feishu-user.json"
        if not os.path.exists(feishu_users_file):
            return jsonify({
                'success': False,
                'message': 'feishu-user.json 文件不存在',
                'data': {
                    'users_with_review': reviewed_authors,
                    'users_without_review': [],
                    'total_feishu_users': 0,
                    'total_reviewed_users': len(reviewed_authors),
                    'time_range': time_description
                }
            }), 404

        with open(feishu_users_file, 'r', encoding='utf-8') as f:
            feishu_users = json.load(f)

        # 提取飞书用户的姓名列表
        feishu_user_names = [user.get('name', '').strip() for user in feishu_users if user.get('name')]

        # 找出没有代码审查记录的人员
        users_without_review = []
        for user in feishu_users:
            user_name = user.get('name', '').strip()
            if user_name and user_name not in reviewed_authors:
                # 只保留必要的用户信息
                user_info = {
                    'name': user_name,
                    'mobile': user.get('mobile', ''),
                    'email': user.get('email', ''),
                    'job_title': user.get('job_title', ''),
                    'department_name': '',
                    'is_activated': user.get('status', {}).get('is_activated', False),
                    'is_exited': user.get('status', {}).get('is_exited', False)
                }

                # 获取部门信息
                if user.get('department_path') and len(user['department_path']) > 0:
                    user_info['department_name'] = user['department_path'][0].get('department_name', {}).get('name', '')

                users_without_review.append(user_info)

        # 构建返回数据
        result = {
            'success': True,
            'message': f'成功分析用户代码审查记录（{time_description}）',
            'data': {
                'users_with_review': reviewed_authors,
                'users_without_review': users_without_review,
                'total_feishu_users': len(feishu_users),
                'total_reviewed_users': len(reviewed_authors),
                'total_unreviewed_users': len(users_without_review),
                'review_coverage_rate': round(len(reviewed_authors) / len(feishu_user_names) * 100, 2) if feishu_user_names else 0,
                'time_range': time_description,
                'query_params': {
                    'time_range': time_range,
                    'start_time': start_time,
                    'end_time': end_time
                }
            }
        }

        logger.info(f"Analysis complete ({time_description}): {len(users_without_review)} users without review records")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error analyzing users without review: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'分析用户代码审查记录时出错: {str(e)}',
            'data': {}
        }), 500


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
        logger.info("Scheduler started successfully.")

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

        # 判断是GitLab还是GitHub的webhook
        webhook_source = request.headers.get('X-GitHub-Event')

        if webhook_source:  # GitHub webhook
            return handle_github_webhook(webhook_source, data)
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
    else:
        error_message = f'Only merge_request and push events are supported (both Webhook and System Hook), but received: {object_kind}.'
        logger.error(error_message)
        return jsonify(error_message), 400


if __name__ == '__main__':
    check_config()
    # 启动定时任务调度器
    setup_scheduler()

    # 启动Flask API服务
    port = int(os.environ.get('SERVER_PORT', 5001))
    api_app.run(host='0.0.0.0', port=port)
