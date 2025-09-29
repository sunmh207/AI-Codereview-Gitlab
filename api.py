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
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import hashlib
import hmac
import base64
import time

from biz.gitlab.webhook_handler import slugify_url
from biz.queue.worker import handle_merge_request_event, handle_push_event, handle_github_pull_request_event, \
    handle_github_push_event
from biz.service.review_service import ReviewService
from biz.utils.im import notifier
from biz.utils.log import logger
from biz.utils.queue import handle_queue
from biz.utils.reporter import Reporter

from biz.utils.config_checker import check_config

api_app = Flask(__name__)

# Configure CORS - Allow all origins for development
CORS(api_app, origins=["*"])

# Configure JWT
api_app.config['JWT_SECRET_KEY'] = os.environ.get('DASHBOARD_SECRET_KEY', 'fac8cf149bdd616c07c1a675c4571ccacc40d7f7fe16914cfe0f9f9d966bb773')
api_app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # Token never expires
jwt = JWTManager(api_app)

# User credentials from environment
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")
USER_CREDENTIALS = {
    DASHBOARD_USER: DASHBOARD_PASSWORD
}

push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'


# Health check endpoint
@api_app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'service': 'AI Code Review API',
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200


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
        # 生成日报内容
        report_txt = Reporter().generate_report(json.dumps(commits))
        # 发送钉钉通知
        notifier.send_notification(content=report_txt, msg_type="markdown", title="代码提交日报")

        # 返回生成的日报内容
        return json.dumps(report_txt, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        return jsonify({'message': f"Failed to generate daily report: {e}"}), 500


# Authentication endpoints
@api_app.route('/api/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'message': 'Username and password are required'}), 400

        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            access_token = create_access_token(identity=username)
            return jsonify({
                'access_token': access_token,
                'username': username,
                'message': 'Login successful'
            }), 200
        else:
            return jsonify({'message': 'Invalid username or password'}), 401
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'message': 'Login failed'}), 500


@api_app.route('/api/auth/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify JWT token"""
    current_user = get_jwt_identity()
    return jsonify({'username': current_user, 'valid': True}), 200


@api_app.route('/api/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout endpoint"""
    return jsonify({'message': 'Logout successful'}), 200


# Data endpoints
@api_app.route('/api/reviews/mr', methods=['GET'])
@jwt_required()
def get_mr_reviews():
    """Get merge request review data with pagination"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        authors = request.args.getlist('authors')
        project_names = request.args.getlist('project_names')
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        # Sorting parameters
        sort_by = request.args.get('sort_by', 'updated_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Score filtering
        score_min = request.args.get('score_min', type=int)
        score_max = request.args.get('score_max', type=int)

        # Convert dates to timestamps
        start_timestamp = None
        end_timestamp = None
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            start_timestamp = int(start_datetime.timestamp())
        if end_date:
            # For end_date, add time to include the entire day (23:59:59)
            if 'T' not in end_date:
                end_date_with_time = end_date + 'T23:59:59'
            else:
                end_date_with_time = end_date
            end_datetime = datetime.fromisoformat(end_date_with_time.replace('Z', '+00:00'))
            end_timestamp = int(end_datetime.timestamp())

        # Get data from service
        df = ReviewService().get_mr_review_logs(
            authors=authors if authors else None,
            project_names=project_names if project_names else None,
            updated_at_gte=start_timestamp,
            updated_at_lte=end_timestamp
        )

        if df.empty:
            return jsonify({'data': [], 'total': 0, 'page': page, 'page_size': page_size}), 200

        # Apply score filtering
        if score_min is not None:
            df = df[df['score'] >= score_min]
        if score_max is not None:
            df = df[df['score'] <= score_max]

        # Apply sorting
        if sort_by in df.columns:
            ascending = sort_order.lower() == 'asc'
            df = df.sort_values(by=sort_by, ascending=ascending)

        # Get total count before pagination
        total = len(df)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        df_page = df.iloc[start_idx:end_idx]

        # Format timestamps
        if "updated_at" in df_page.columns:
            df_page = df_page.copy()
            df_page["updated_at"] = df_page["updated_at"].apply(
                lambda ts: datetime.fromtimestamp(ts).isoformat() + 'Z'
                if isinstance(ts, (int, float)) else ts
            )

        # Convert to records
        records = df_page.to_dict('records')
        
        return jsonify({
            'data': records, 
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }), 200

    except Exception as e:
        logger.error(f"Get MR reviews error: {e}")
        return jsonify({'message': 'Failed to get MR reviews'}), 500


@api_app.route('/api/reviews/push', methods=['GET'])
@jwt_required()
def get_push_reviews():
    """Get push review data with pagination"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        authors = request.args.getlist('authors')
        project_names = request.args.getlist('project_names')
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        # Sorting parameters
        sort_by = request.args.get('sort_by', 'updated_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Score filtering
        score_min = request.args.get('score_min', type=int)
        score_max = request.args.get('score_max', type=int)

        # Convert dates to timestamps
        start_timestamp = None
        end_timestamp = None
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            start_timestamp = int(start_datetime.timestamp())
        if end_date:
            # For end_date, add time to include the entire day (23:59:59)
            if 'T' not in end_date:
                end_date_with_time = end_date + 'T23:59:59'
            else:
                end_date_with_time = end_date
            end_datetime = datetime.fromisoformat(end_date_with_time.replace('Z', '+00:00'))
            end_timestamp = int(end_datetime.timestamp())

        # Get data from service
        df = ReviewService().get_push_review_logs(
            authors=authors if authors else None,
            project_names=project_names if project_names else None,
            updated_at_gte=start_timestamp,
            updated_at_lte=end_timestamp
        )

        if df.empty:
            return jsonify({'data': [], 'total': 0, 'page': page, 'page_size': page_size}), 200

        # Apply score filtering
        if score_min is not None:
            df = df[df['score'] >= score_min]
        if score_max is not None:
            df = df[df['score'] <= score_max]

        # Apply sorting
        if sort_by in df.columns:
            ascending = sort_order.lower() == 'asc'
            df = df.sort_values(by=sort_by, ascending=ascending)

        # Get total count before pagination
        total = len(df)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        df_page = df.iloc[start_idx:end_idx]

        # Format timestamps
        if "updated_at" in df_page.columns:
            df_page = df_page.copy()
            df_page["updated_at"] = df_page["updated_at"].apply(
                lambda ts: datetime.fromtimestamp(ts).isoformat() + 'Z'
                if isinstance(ts, (int, float)) else ts
            )

        # Convert to records
        records = df_page.to_dict('records')
        
        return jsonify({
            'data': records, 
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }), 200

    except Exception as e:
        logger.error(f"Get push reviews error: {e}")
        return jsonify({'message': 'Failed to get push reviews'}), 500


@api_app.route('/api/statistics/projects', methods=['GET'])
@jwt_required()
def get_project_statistics():
    """Get project statistics"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        review_type = request.args.get('type', 'mr')  # 'mr' or 'push'

        # Convert dates to timestamps
        start_timestamp = None
        end_timestamp = None
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            start_timestamp = int(start_datetime.timestamp())
        if end_date:
            # For end_date, add time to include the entire day (23:59:59)
            if 'T' not in end_date:
                end_date_with_time = end_date + 'T23:59:59'
            else:
                end_date_with_time = end_date
            end_datetime = datetime.fromisoformat(end_date_with_time.replace('Z', '+00:00'))
            end_timestamp = int(end_datetime.timestamp())

        # Get data from service
        if review_type == 'push':
            df = ReviewService().get_push_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )
        else:
            df = ReviewService().get_mr_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )

        if df.empty:
            return jsonify({'project_counts': [], 'project_scores': []}), 200

        # Calculate project statistics
        project_counts = df['project_name'].value_counts().reset_index()
        project_counts.columns = ['project_name', 'count']

        project_scores = df.groupby('project_name')['score'].mean().reset_index()
        project_scores.columns = ['project_name', 'average_score']

        return jsonify({
            'project_counts': project_counts.to_dict('records'),
            'project_scores': project_scores.to_dict('records')
        }), 200

    except Exception as e:
        logger.error(f"Get project statistics error: {e}")
        return jsonify({'message': 'Failed to get project statistics'}), 500


@api_app.route('/api/statistics/authors', methods=['GET'])
@jwt_required()
def get_author_statistics():
    """Get author statistics"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        review_type = request.args.get('type', 'mr')  # 'mr' or 'push'

        # Convert dates to timestamps
        start_timestamp = None
        end_timestamp = None
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            start_timestamp = int(start_datetime.timestamp())
        if end_date:
            # For end_date, add time to include the entire day (23:59:59)
            if 'T' not in end_date:
                end_date_with_time = end_date + 'T23:59:59'
            else:
                end_date_with_time = end_date
            end_datetime = datetime.fromisoformat(end_date_with_time.replace('Z', '+00:00'))
            end_timestamp = int(end_datetime.timestamp())

        # Get data from service
        if review_type == 'push':
            df = ReviewService().get_push_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )
        else:
            df = ReviewService().get_mr_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )

        if df.empty:
            return jsonify({
                'author_counts': [],
                'author_scores': [],
                'author_code_lines': []
            }), 200

        # Calculate author statistics
        author_counts = df['author'].value_counts().reset_index()
        author_counts.columns = ['author', 'count']

        author_scores = df.groupby('author')['score'].mean().reset_index()
        author_scores.columns = ['author', 'average_score']

        # Calculate code lines statistics
        author_code_lines = df.groupby('author').agg({
            'additions': 'sum',
            'deletions': 'sum'
        }).reset_index()

        return jsonify({
            'author_counts': author_counts.to_dict('records'),
            'author_scores': author_scores.to_dict('records'),
            'author_code_lines': author_code_lines.to_dict('records')
        }), 200

    except Exception as e:
        logger.error(f"Get author statistics error: {e}")
        return jsonify({'message': 'Failed to get author statistics'}), 500


@api_app.route('/api/statistics/<stat_type>', methods=['GET'])
@jwt_required()
def get_statistics(stat_type):
    """Get specific statistics by type"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        review_type = request.args.get('type', 'mr')  # 'mr' or 'push'

        # Convert dates to timestamps
        start_timestamp = None
        end_timestamp = None
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            start_timestamp = int(start_datetime.timestamp())
        if end_date:
            # For end_date, add time to include the entire day (23:59:59)
            if 'T' not in end_date:
                end_date_with_time = end_date + 'T23:59:59'
            else:
                end_date_with_time = end_date
            end_datetime = datetime.fromisoformat(end_date_with_time.replace('Z', '+00:00'))
            end_timestamp = int(end_datetime.timestamp())

        # Get data from service
        if review_type == 'push':
            df = ReviewService().get_push_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )
        else:
            df = ReviewService().get_mr_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )

        if df.empty:
            return jsonify({'data': []}), 200

        # Calculate statistics based on type
        if stat_type == 'project_counts':
            result = df['project_name'].value_counts().reset_index()
            result.columns = ['project_name', 'count']
        elif stat_type == 'project_scores':
            result = df.groupby('project_name')['score'].mean().reset_index()
            result.columns = ['project_name', 'average_score']
        elif stat_type == 'author_counts':
            result = df['author'].value_counts().reset_index()
            result.columns = ['author', 'count']
        elif stat_type == 'author_scores':
            result = df.groupby('author')['score'].mean().reset_index()
            result.columns = ['author', 'average_score']
        elif stat_type == 'author_code_lines':
            result = df.groupby('author').agg({
                'additions': 'sum',
                'deletions': 'sum'
            }).reset_index()
        else:
            return jsonify({'message': 'Invalid statistics type'}), 400

        return jsonify({'data': result.to_dict('records')}), 200

    except Exception as e:
        logger.error(f"Get statistics error: {e}")
        return jsonify({'message': 'Failed to get statistics'}), 500

        # Calculate code lines if available
        author_code_lines = []
        if 'additions' in df.columns and 'deletions' in df.columns:
            author_additions = df.groupby('author')['additions'].sum().reset_index()
            author_deletions = df.groupby('author')['deletions'].sum().reset_index()
            author_code_lines = []
            for _, row in author_additions.iterrows():
                author = row['author']
                additions = row['additions']
                deletions = author_deletions[author_deletions['author'] == author]['deletions'].iloc[0] if not author_deletions[author_deletions['author'] == author].empty else 0
                author_code_lines.append({
                    'author': author,
                    'additions': additions,
                    'deletions': deletions
                })

        return jsonify({
            'author_counts': author_counts.to_dict('records'),
            'author_scores': author_scores.to_dict('records'),
            'author_code_lines': author_code_lines
        }), 200

    except Exception as e:
        logger.error(f"Get author statistics error: {e}")
        return jsonify({'message': 'Failed to get author statistics'}), 500


@api_app.route('/api/metadata', methods=['GET'])
@jwt_required()
def get_metadata():
    """Get metadata for filters"""
    try:
        # Get query parameters for date range
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        review_type = request.args.get('type', 'mr')  # 'mr' or 'push'

        # Convert dates to timestamps
        start_timestamp = None
        end_timestamp = None
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            start_timestamp = int(start_datetime.timestamp())
        if end_date:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            end_timestamp = int(end_datetime.timestamp())

        # Get data from service
        if review_type == 'push':
            df = ReviewService().get_push_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )
        else:
            df = ReviewService().get_mr_review_logs(
                updated_at_gte=start_timestamp,
                updated_at_lte=end_timestamp
            )

        if df.empty:
            return jsonify({
                'authors': [],
                'project_names': [],
                'push_review_enabled': push_review_enabled
            }), 200

        # Get unique values
        authors = sorted(df["author"].dropna().unique().tolist())
        project_names = sorted(df["project_name"].dropna().unique().tolist())

        return jsonify({
            'authors': authors,
            'project_names': project_names,
            'push_review_enabled': push_review_enabled
        }), 200

    except Exception as e:
        logger.error(f"Get metadata error: {e}")
        return jsonify({'message': 'Failed to get metadata'}), 500


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
