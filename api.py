from dotenv import load_dotenv

load_dotenv("conf/.env")

import atexit
import json
import os
import traceback
from datetime import datetime
from urllib.parse import urlparse
import hmac
import hashlib
import base64
import time
import jwt

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, request, jsonify
from flask_cors import CORS

from biz.gitlab.webhook_handler import slugify_url
from biz.queue.worker import handle_merge_request_event, handle_push_event, handle_github_pull_request_event, \
    handle_github_push_event
from biz.service.review_service import ReviewService
from biz.utils.log import logger
from biz.utils.queue import handle_queue
from biz.utils.daily_report_service import DailyReportService

from biz.utils.config_checker import check_config

api_app = Flask(__name__)
CORS(api_app)  # 启用跨域支持

push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'

# 从环境变量中读取用户名和密码
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")
USER_CREDENTIALS = {
    DASHBOARD_USER: DASHBOARD_PASSWORD
}

# 用于生成和验证token的密钥
SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "fac8cf149bdd616c07c1a675c4571ccacc40d7f7fe16914cfe0f9f9d966bb773")


def generate_jwt_token(username):
    """生成JWT token"""
    payload = {
        'username': username,
        'iat': int(time.time()),
        'exp': int(time.time()) + (30 * 24 * 60 * 60)  # 30天过期
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token


def verify_jwt_token(token):
    """验证JWT token的有效性并提取用户名"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload.get('username')
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid token")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


def format_timestamp_to_datetime(timestamp):
    """将时间戳转换为日期时间字符串"""
    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    return timestamp


def format_delta(additions, deletions):
    """格式化代码变更量"""
    if additions is not None and deletions is not None:
        return f"+{int(additions)} -{int(deletions)}"
    return ""


@api_app.route('/')
def home():
    return """<h2>The code review api server is running.</h2>
              <p>GitHub project address: <a href="https://github.com/sunmh207/AI-Codereview-Gitlab" target="_blank">
              https://github.com/sunmh207/AI-Codereview-Gitlab</a></p>
              <p>Gitee project address: <a href="https://gitee.com/sunminghui/ai-codereview-gitlab" target="_blank">https://gitee.com/sunminghui/ai-codereview-gitlab</a></p>
              """


# ==================== Vue3 前端 API 接口 ====================

@api_app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录接口"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        remember = data.get('remember', False)

        if not username or not password:
            return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400

        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            response_data = {
                'success': True,
                'message': '登录成功',
                'user': {'username': username}
            }

            if remember:
                token = generate_jwt_token(username)
                response_data['token'] = token

            return jsonify(response_data)
        else:
            return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'message': '登录失败'}), 500


@api_app.route('/api/auth/verify', methods=['POST'])
def verify_auth():
    """验证token接口"""
    try:
        data = request.get_json()
        token = data.get('token')

        if not token:
            return jsonify({'success': False, 'message': 'Token不能为空'}), 400

        username = verify_jwt_token(token)
        if username and username in USER_CREDENTIALS:
            return jsonify({
                'success': True,
                'user': {'username': username}
            })
        else:
            return jsonify({'success': False, 'message': 'Token无效或已过期'}), 401

    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return jsonify({'success': False, 'message': '验证失败'}), 500


@api_app.route('/api/mr-logs', methods=['GET'])
def get_mr_logs():
    """获取合并请求审查日志"""
    try:
        # 获取查询参数
        authors = request.args.getlist('authors')
        project_names = request.args.getlist('project_names')
        updated_at_gte = request.args.get('updated_at_gte', type=int)
        updated_at_lte = request.args.get('updated_at_lte', type=int)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)

        # 调用服务获取数据
        df = ReviewService().get_mr_review_logs(
            authors=authors if authors else None,
            project_names=project_names if project_names else None,
            updated_at_gte=updated_at_gte,
            updated_at_lte=updated_at_lte
        )

        if df.empty:
            return jsonify({
                'success': True,
                'data': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            })

        # 处理数据格式
        df["updated_at"] = df["updated_at"].apply(format_timestamp_to_datetime)
        df["delta"] = df.apply(lambda row: format_delta(row.get('additions'), row.get('deletions')), axis=1)

        # 计算分页
        total = len(df)
        total_pages = (total + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        # 获取当前页数据
        page_data = df.iloc[start_idx:end_idx].to_dict(orient='records')

        return jsonify({
            'success': True,
            'data': page_data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        })

    except Exception as e:
        logger.error(f"Get MR logs error: {e}")
        return jsonify({'success': False, 'message': '获取合并请求日志失败'}), 500


@api_app.route('/api/push-logs', methods=['GET'])
def get_push_logs():
    """获取推送审查日志"""
    try:
        # 获取查询参数
        authors = request.args.getlist('authors')
        project_names = request.args.getlist('project_names')
        updated_at_gte = request.args.get('updated_at_gte', type=int)
        updated_at_lte = request.args.get('updated_at_lte', type=int)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)

        # 调用服务获取数据
        df = ReviewService().get_push_review_logs(
            authors=authors if authors else None,
            project_names=project_names if project_names else None,
            updated_at_gte=updated_at_gte,
            updated_at_lte=updated_at_lte
        )

        if df.empty:
            return jsonify({
                'success': True,
                'data': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            })

        # 处理数据格式
        df["updated_at"] = df["updated_at"].apply(format_timestamp_to_datetime)
        df["delta"] = df.apply(lambda row: format_delta(row.get('additions'), row.get('deletions')), axis=1)

        # 计算分页
        total = len(df)
        total_pages = (total + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        # 获取当前页数据
        page_data = df.iloc[start_idx:end_idx].to_dict(orient='records')

        return jsonify({
            'success': True,
            'data': page_data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        })

    except Exception as e:
        logger.error(f"Get push logs error: {e}")
        return jsonify({'success': False, 'message': '获取推送日志失败'}), 500


@api_app.route('/api/projects', methods=['GET'])
def get_projects():
    """获取项目列表"""
    try:
        # 从MR和Push日志中获取所有项目名称
        mr_df = ReviewService().get_mr_review_logs()
        push_df = ReviewService().get_push_review_logs()

        projects = set()

        if not mr_df.empty and 'project_name' in mr_df.columns:
            projects.update(mr_df['project_name'].dropna().unique())

        if not push_df.empty and 'project_name' in push_df.columns:
            projects.update(push_df['project_name'].dropna().unique())

        project_list = sorted(list(projects))

        return jsonify({'success': True, 'data': project_list})

    except Exception as e:
        logger.error(f"Get projects error: {e}")
        return jsonify({'success': False, 'message': '获取项目列表失败'}), 500


@api_app.route('/api/authors', methods=['GET'])
def get_authors():
    """获取开发者列表"""
    try:
        # 从MR和Push日志中获取所有开发者
        mr_df = ReviewService().get_mr_review_logs()
        push_df = ReviewService().get_push_review_logs()

        authors = set()

        if not mr_df.empty and 'author' in mr_df.columns:
            authors.update(mr_df['author'].dropna().unique())

        if not push_df.empty and 'author' in push_df.columns:
            authors.update(push_df['author'].dropna().unique())

        author_list = sorted(list(authors))

        return jsonify({'success': True, 'data': author_list})

    except Exception as e:
        logger.error(f"Get authors error: {e}")
        return jsonify({'success': False, 'message': '获取开发者列表失败'}), 500


@api_app.route('/api/mr-logs/all', methods=['GET'])
def get_all_mr_logs():
    """获取所有合并请求审查日志（用于图表统计）"""
    try:
        # 获取查询参数（不包含分页）
        authors = request.args.getlist('authors')
        project_names = request.args.getlist('project_names')
        updated_at_gte = request.args.get('updated_at_gte', type=int)
        updated_at_lte = request.args.get('updated_at_lte', type=int)

        # 调用服务获取所有数据
        df = ReviewService().get_mr_review_logs(
            authors=authors if authors else None,
            project_names=project_names if project_names else None,
            updated_at_gte=updated_at_gte,
            updated_at_lte=updated_at_lte
        )

        if df.empty:
            return jsonify({'success': True, 'data': []})

        # 处理数据格式
        df["updated_at"] = df["updated_at"].apply(format_timestamp_to_datetime)
        df["delta"] = df.apply(lambda row: format_delta(row.get('additions'), row.get('deletions')), axis=1)

        # 转换为字典列表
        data = df.to_dict(orient='records')

        return jsonify({'success': True, 'data': data})

    except Exception as e:
        logger.error(f"Get all MR logs error: {e}")
        return jsonify({'success': False, 'message': '获取所有合并请求日志失败'}), 500


@api_app.route('/api/push-logs/all', methods=['GET'])
def get_all_push_logs():
    """获取所有推送审查日志（用于图表统计）"""
    try:
        # 获取查询参数（不包含分页）
        authors = request.args.getlist('authors')
        project_names = request.args.getlist('project_names')
        updated_at_gte = request.args.get('updated_at_gte', type=int)
        updated_at_lte = request.args.get('updated_at_lte', type=int)

        # 调用服务获取所有数据
        df = ReviewService().get_push_review_logs(
            authors=authors if authors else None,
            project_names=project_names if project_names else None,
            updated_at_gte=updated_at_gte,
            updated_at_lte=updated_at_lte
        )

        if df.empty:
            return jsonify({'success': True, 'data': []})

        # 处理数据格式
        df["updated_at"] = df["updated_at"].apply(format_timestamp_to_datetime)
        df["delta"] = df.apply(lambda row: format_delta(row.get('additions'), row.get('deletions')), axis=1)

        # 转换为字典列表
        data = df.to_dict(orient='records')

        return jsonify({'success': True, 'data': data})

    except Exception as e:
        logger.error(f"Get all push logs error: {e}")
        return jsonify({'success': False, 'message': '获取所有推送日志失败'}), 500


@api_app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置信息"""
    try:
        config = {
            'push_review_enabled': push_review_enabled,
            'dashboard_user': DASHBOARD_USER,
            'show_security_warning': DASHBOARD_USER == 'admin' and DASHBOARD_PASSWORD == 'admin'
        }

        return jsonify({'success': True, 'data': config})

    except Exception as e:
        logger.error(f"Get config error: {e}")
        return jsonify({'success': False, 'message': '获取配置失败'}), 500


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
