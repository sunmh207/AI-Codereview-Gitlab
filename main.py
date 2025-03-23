import atexit
import json
import re
import os
import traceback
from datetime import datetime
from multiprocessing import Process
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv, find_dotenv
from flask import Flask, request, jsonify, send_from_directory, Response

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.event.event_manager import event_manager
from biz.gitlab.webhook_handler import MergeRequestHandler, PushHandler
from biz.service.review_service import ReviewService
from biz.utils.code_reviewer import CodeReviewer
from biz.utils.im import im_notifier
from biz.utils.log import logger
from biz.utils.reporter import Reporter
from urllib.parse import urlparse

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import pandas as pd
from biz.service.review_service import ReviewService
from datetime import datetime, timedelta
from flask_cors import CORS
from biz.llm.factory import Factory
from biz.llm.types import NOT_GIVEN

load_dotenv("conf/.env")
api_app = Flask(__name__)
api_app.secret_key = os.getenv('FLASK_SECRET_KEY', 'ai123456789!!!')  # 新增此行
CORS(api_app, resources={r"/*": {"origins": "*"}}) 

PUSH_REVIEW_ENABLED = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'


@api_app.route('/')
def home():
    return send_from_directory('static', 'index.html')

@api_app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('static/js', filename)

@api_app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('static/css', filename)

@api_app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@api_app.route('/review/daily_report', methods=['GET'])
def daily_report():
    # 获取当前日期0点和23点59分59秒的时间戳
    start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    end_time = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).timestamp()

    try:
        if PUSH_REVIEW_ENABLED:
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
        im_notifier.send_notification(content=report_txt, msg_type="markdown", title="代码提交日报")

        # 返回生成的日报内容
        return json.dumps(report_txt, ensure_ascii=False, indent=4)
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


# 提示词模板库 CRUD API
import yaml

prompts = []

def get_agent_prompt_file(agent):
    """获取指定agent的提示词模板文件路径"""
    return os.path.join('conf', 'agents', agent, 'prompt_templates.yml')

@api_app.route('/api/agents', methods=['GET'])
def get_agents():
    """获取所有可用的agents列表"""
    try:
        agents_dir = os.path.join('conf', 'agents')
        if not os.path.exists(agents_dir):
            return jsonify(['default'])
            
        agents = []
        for item in os.listdir(agents_dir):
            if os.path.isdir(os.path.join(agents_dir, item)):
                agents.append(item)
                
        if not agents:
            return jsonify(['default'])
            
        return jsonify(agents)
    except Exception as e:
        logger.error(f"Error getting agents list: {str(e)}")
        return jsonify({'error': 'Failed to get agents list'}), 500

@api_app.route('/api/prompt-templates/<agent>', methods=['GET'])
def get_prompt_templates(agent):
    """获取指定agent的提示词模板"""
    try:
        prompt_file = get_agent_prompt_file(agent)
        if not os.path.exists(prompt_file):
            return jsonify({})
            
        with open(prompt_file, 'r', encoding='utf-8') as file:
            templates = yaml.safe_load(file) or {}
        return jsonify(templates)
    except Exception as e:
        logger.error(f"Error reading prompt templates for agent {agent}: {str(e)}")
        return jsonify({'error': 'Failed to read prompt templates'}), 500

@api_app.route('/api/prompt-templates/<agent>', methods=['PUT'])
def update_prompt_templates(agent):
    """更新指定agent的提示词模板"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        prompt_file = get_agent_prompt_file(agent)
        os.makedirs(os.path.dirname(prompt_file), exist_ok=True)
            
        # 读取现有的模板
        existing_templates = {}
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r', encoding='utf-8') as file:
                existing_templates = yaml.safe_load(file) or {}
            
        # 更新特定的模板
        for key, value in data.items():
            existing_templates[key] = value
            
        # 保存更新后的所有模板，使用自定义格式化
        with open(prompt_file, 'w', encoding='utf-8') as file:
            for key, value in existing_templates.items():
                # 使用 |- 来保持原始格式
                file.write(f"{key}: |-\n")
                # 确保内容有正确的缩进
                for line in value.split('\n'):
                    file.write(f"  {line}\n")
                file.write('\n')  # 在每个模板之间添加空行
            
        return jsonify({'message': 'Successfully updated prompt templates'})
    except Exception as e:
        logger.error(f"Error updating prompt templates for agent {agent}: {str(e)}")
        return jsonify({'error': 'Failed to update prompt templates'}), 500

@api_app.route('/api/prompt-templates/<agent>', methods=['POST'])
def create_prompt_template(agent):
    """创建新的提示词模板"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        prompt_file = get_agent_prompt_file(agent)
        os.makedirs(os.path.dirname(prompt_file), exist_ok=True)
            
        # 读取现有的模板
        existing_templates = {}
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r', encoding='utf-8') as file:
                existing_templates = yaml.safe_load(file) or {}
            
        # 添加新的模板
        for key, value in data.items():
            existing_templates[key] = value
            
        # 保存更新后的所有模板
        with open(prompt_file, 'w', encoding='utf-8') as file:
            for key, value in existing_templates.items():
                file.write(f"{key}: |-\n")
                for line in value.split('\n'):
                    file.write(f"  {line}\n")
                file.write('\n')
            
        return jsonify({'message': 'Successfully created prompt template'})
    except Exception as e:
        logger.error(f"Error creating prompt template for agent {agent}: {str(e)}")
        return jsonify({'error': 'Failed to create prompt template'}), 500

@api_app.route('/api/prompt-templates/<agent>/<template_id>', methods=['DELETE'])
def delete_prompt_template(agent, template_id):
    """删除指定的提示词模板"""
    try:
        prompt_file = get_agent_prompt_file(agent)
        if not os.path.exists(prompt_file):
            return jsonify({'error': 'Template file not found'}), 404
            
        # 读取现有的模板
        with open(prompt_file, 'r', encoding='utf-8') as file:
            templates = yaml.safe_load(file) or {}
            
        # 删除指定的模板
        if template_id in templates:
            del templates[template_id]
            
            # 保存更新后的模板
            with open(prompt_file, 'w', encoding='utf-8') as file:
                for key, value in templates.items():
                    file.write(f"{key}: |-\n")
                    for line in value.split('\n'):
                        file.write(f"  {line}\n")
                    file.write('\n')
                    
            return jsonify({'message': 'Successfully deleted prompt template'})
        else:
            return jsonify({'error': 'Template not found'}), 404
            
    except Exception as e:
        logger.error(f"Error deleting prompt template for agent {agent}: {str(e)}")
        return jsonify({'error': 'Failed to delete prompt template'}), 500

@api_app.route('/api/prompts', methods=['GET'])
def get_prompts():
    return jsonify(prompts)

@api_app.route('/api/prompts', methods=['POST'])
def create_prompt():
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'error': 'Invalid data'}), 400
    new_prompt = {'id': len(prompts) + 1, 'content': data['content']}
    prompts.append(new_prompt)
    return jsonify(new_prompt), 201

@api_app.route('/api/prompts/<int:id>', methods=['PUT'])
def update_prompt(id):
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'error': 'Invalid data'}), 400
    for prompt in prompts:
        if prompt['id'] == id:
            prompt['content'] = data['content']
            return jsonify(prompt)
    return jsonify({'error': 'Prompt not found'}), 404

@api_app.route('/api/prompts/<int:id>', methods=['DELETE'])
def delete_prompt(id):
    global prompts
    prompts = [prompt for prompt in prompts if prompt['id'] != id]
    return jsonify({'message': 'Prompt deleted'}), 200

# 处理 GitLab Merge Request Webhook
@api_app.route('/review/webhook', methods=['POST'])
def handle_webhook():
    # 获取请求的JSON数据
    if request.is_json:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        object_kind = data.get("object_kind")
        print("Request Headers:")
        for key, value in request.headers.items():
            print(f"  {key}: {value}")
        print(data)

        # 优先从请求头获取，如果没有，则从环境变量获取，如果没有，则从推送事件中获取
        gitlab_url = os.getenv('GITLAB_URL') or request.headers.get('X-Gitlab-Instance')
        if not gitlab_url:
            repository = data.get('repository')
            if not repository:
                return jsonify({'message': 'Missing GitLab URL 1'}), 400
            homepage = repository.get("homepage")
            if not homepage:
                return jsonify({'message': 'Missing GitLab URL 2'}), 400
            try:
                parsed_url = urlparse(homepage)
                gitlab_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
                print(gitlab_url)
            except Exception as e:
                return jsonify({"error": f"Failed to parse homepage URL: {str(e)}"}), 400

        # 优先从环境变量获取，如果没有，则从请求头获取
        gitlab_token = os.getenv('GITLAB_ACCESS_TOKEN') or request.headers.get('X-Gitlab-Token')
        # 如果gitlab_token为空，返回错误
        if not gitlab_token:
            return jsonify({'message': 'Missing GitLab access token'}), 400

        # 打印整个payload数据，或根据需求进行处理
        logger.info(f'Received event: {object_kind}')
        logger.info(f'Payload: {json.dumps(data)}')

        # 处理Merge Request Hook
        if object_kind == "merge_request":
            # 创建一个新进程进行异步处理
            process = Process(target=__handle_merge_request_event, args=(data, gitlab_token, gitlab_url))
            process.start()
            # 立马返回响应
            return jsonify(
                {'message': f'Request received(object_kind={object_kind}), will process asynchronously.'}), 200
        elif object_kind == "push":
            # 创建一个新进程进行异步处理
            process = Process(target=__handle_push_event, args=(data, gitlab_token, gitlab_url))
            process.start()
            # 立马返回响应
            return jsonify(
                {'message': f'Request received(object_kind={object_kind}), will process asynchronously.'}), 200
        else:
            error_message = f'Only merge_request and push events are supported (both Webhook and System Hook), but received: {object_kind}.'
            logger.error(error_message)
            return jsonify(error_message), 400
    else:
        return jsonify({'message': 'Invalid data format'}), 400


def slugify_url(original_url: str) -> str:
    """
    将原始URL转换为适合作为文件名的字符串，其中非字母或数字的字符会被替换为下划线，举例：
    slugify_url("http://example.com/path/to/repo/") => example_com_path_to_repo
    slugify_url("https://gitlab.com/user/repo.git") => gitlab_com_user_repo_git
    """
    # Remove URL scheme (http, https, etc.) if present
    original_url = re.sub(r'^https?://', '', original_url)

    # Replace non-alphanumeric characters (except underscore) with underscores
    target = re.sub(r'[^a-zA-Z0-9]', '_', original_url)

    # Remove trailing underscore if present
    target = target.rstrip('_')

    return target


def __handle_push_event(webhook_data: dict, gitlab_token: str, gitlab_url: str):
    try:
        handler = PushHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Push Hook event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        review_result = None
        score = 0
        if PUSH_REVIEW_ENABLED:
            # 获取PUSH的changes
            changes = handler.get_push_changes()
            logger.info('changes: %s', changes)
            changes = filter_changes(changes)
            if not changes:
                logger.info('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
                return
            review_result = "关注的文件没有修改"

            if len(changes) > 0:
                commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                review_result = review_code(str(changes), commits_text)
                score = CodeReviewer.parse_review_score(review_text=review_result)
            # 将review结果提交到Gitlab的 notes
            handler.add_push_notes(f'Auto Review Result: \n{review_result}')


        event_manager['push_reviewed'].send(PushReviewEntity(
            project_name=webhook_data['project']['name'],
            author=webhook_data['user_username'],
            branch=webhook_data['project']['default_branch'],
            updated_at=int(datetime.now().timestamp()),  # 当前时间
            commits=commits,
            score=score,
            review_result=review_result,
            gitlab_url_slug = slugify_url(gitlab_url),
        ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        im_notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def __handle_merge_request_event(webhook_data: dict, gitlab_token: str, gitlab_url: str):
    '''
    处理Merge Request Hook事件
    :param webhook_data:
    :param gitlab_token:
    :param gitlab_url:
    :return:
    '''
    try:
        # 解析Webhook数据
        handler = MergeRequestHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Merge Request Hook event received')

        if (handler.action in ['open', 'update']):  # 仅仅在MR创建或更新时进行Code Review
            # 获取Merge Request的changes
            changes = handler.get_merge_request_changes()
            logger.info('changes: %s', changes)
            changes = filter_changes(changes)
            if not changes:
                logger.info('未检测到有关代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
                return

            # 获取Merge Request的commits
            commits = handler.get_merge_request_commits()
            if not commits:
                logger.error('Failed to get commits')
                return

            # review 代码
            commits_text = ';'.join(commit['title'] for commit in commits)
            review_result = review_code(str(changes), commits_text)

            if "COT ABORT!" in review_result:
                logger.error('COT ABORT!')
                return

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
                    score=CodeReviewer.parse_review_score(review_text=review_result),
                    url=webhook_data['object_attributes']['url'],
                    review_result=review_result,
                    gitlab_url_slug = slugify_url(gitlab_url),
                )
            )

        else:
            logger.info(f"Merge Request Hook event, action={handler.action}, ignored.")

    except Exception as e:
        error_message = f'AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        im_notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def filter_changes(changes: list):
    '''
    过滤数据，只保留支持的文件类型以及必要的字段信息
    '''
    filter_deleted_files_changes = [change for change in changes if change.get("deleted_file") == False]
    # 从环境变量中获取支持的文件扩展名
    SUPPORTED_EXTENSIONS = os.getenv('SUPPORTED_EXTENSIONS', '.java,.py,.php').split(',')
    # 过滤 `new_path` 以支持的扩展名结尾的元素, 仅保留diff和new_path字段
    filtered_changes = [
        {
            'diff': item.get('diff', ''),
            'new_path': item['new_path']
        }
        for item in filter_deleted_files_changes
        if any(item.get('new_path', '').endswith(ext) for ext in SUPPORTED_EXTENSIONS)
    ]
    return filtered_changes


def review_code(changes_text: str, commits_text: str = '') -> str:
    # 如果超长，取前REVIEW_MAX_LENGTH字符
    review_max_length = int(os.getenv('REVIEW_MAX_LENGTH', 5000))
    # 如果changes为空,打印日志
    if not changes_text:
        logger.info('代码为空, diffs_text = %', str(changes_text))
        return '代码为空'

    if len(changes_text) > review_max_length:
        changes_text = changes_text[:review_max_length]
        logger.info(f'文本超长，截段后content: {changes_text}')

    # 获取启用的评审者列表
    enabled_agents = os.getenv('ENABLED_AGENTS', '').split(',')
    if not enabled_agents or enabled_agents[0] == '':
        enabled_agents = ['code_reviewer']  # 默认使用 code_reviewer

    logger.info(f"Enabled agents: {enabled_agents}")
    logger.info(f"Changes text type: {type(changes_text)}")
    logger.info(f"Changes text content: {changes_text}")

    # 按顺序进行代码评审
    all_reviews = []
    for agent in enabled_agents:
        agent = agent.strip()
        if not agent:
            continue
            
        try:
            # 直接读取 YAML 文件
            prompt_file = get_agent_prompt_file(agent)
            if not os.path.exists(prompt_file):
                logger.error(f"Prompt templates file not found for agent {agent}: {prompt_file}")
                continue
                
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_templates = yaml.safe_load(f)
                system_prompt = prompt_templates.get('system_prompt')
                user_prompt = prompt_templates.get('user_prompt')
                supported_extensions = prompt_templates.get('supported_extensions', [])
                
                if not system_prompt or not user_prompt:
                    logger.error(f"Invalid prompt templates for agent {agent}")
                    continue
                    
                # 检查是否有支持的文件类型
                if supported_extensions:
                    # 从 changes_text 中获取文件路径
                    file_paths = []
                    
                    try:
                        # 尝试解析 changes_text
                        logger.info(f"Attempting to parse changes_text for agent {agent}")
                        if isinstance(changes_text, str):
                            # 如果是字符串，尝试先解析为 Python 对象
                            try:
                                # 使用 ast.literal_eval 安全地解析 Python 字面量
                                import ast
                                changes = ast.literal_eval(changes_text)
                            except (SyntaxError, ValueError):
                                # 如果失败，尝试作为 JSON 解析
                                changes = json.loads(changes_text)
                        else:
                            logger.info("Changes text is not string, using as is")
                            changes = changes_text
                            
                        logger.info(f"Parsed changes type: {type(changes)}")
                        logger.info(f"Parsed changes content: {changes}")
                            
                        # 从 changes 中获取文件路径
                        for change in changes:
                            if isinstance(change, dict):
                                logger.info(f"Processing change: {change}")
                                if 'new_path' in change:
                                    file_paths.append(change['new_path'])
                                    logger.info(f"Added new_path: {change['new_path']}")
                                if 'old_path' in change:
                                    file_paths.append(change['old_path'])
                                    logger.info(f"Added old_path: {change['old_path']}")
                    except Exception as e:
                        logger.error(f"Error parsing changes data: {str(e)}")
                        logger.error(f"Changes text that caused error: {changes_text}")
                        # 如果解析失败，尝试从 changes_text 中获取文件路径
                        if isinstance(changes_text, list):
                            logger.info("Changes text is list, processing directly")
                            for change in changes_text:
                                if isinstance(change, dict):
                                    if 'new_path' in change:
                                        file_paths.append(change['new_path'])
                                        logger.info(f"Added new_path from list: {change['new_path']}")
                                    if 'old_path' in change:
                                        file_paths.append(change['old_path'])
                                        logger.info(f"Added old_path from list: {change['old_path']}")
                    
                    # 去重
                    file_paths = list(set(file_paths))
                    logger.info(f"Final file paths for agent {agent}: {file_paths}")
                    
                    # 检查是否有任何文件匹配支持的文件类型
                    has_supported_files = False
                    for file_path in file_paths:
                        logger.info(f"Checking file path: {file_path}")
                        for ext in supported_extensions:
                            if file_path.lower().endswith(ext.lower()):
                                has_supported_files = True
                                logger.info(f"Found supported extension {ext} in file {file_path}")
                                break
                        if has_supported_files:
                            break
                    
                    if not has_supported_files:
                        logger.info(f"Agent {agent} skipped: No supported file types found. File paths: {file_paths}, Supported extensions: {supported_extensions}")
                        continue
                    
                review_result = CodeReviewer().review_code(
                    str(changes_text),  # 确保传入字符串
                    commits_text,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt
                ).strip()
                
                if review_result.startswith("```markdown") and review_result.endswith("```"):
                    review_result = review_result[11:-3].strip()
                    
                all_reviews.append(f"## {agent.replace('_', ' ').title()} 评审结果\n\n{review_result}\n")
                
        except Exception as e:
            logger.error(f"Error in {agent} review: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            continue

    # 合并所有评审结果
    if not all_reviews:
        return "代码评审失败，请检查配置和日志"
        
    return "\n\n".join(all_reviews)


@api_app.route('/api/push-logs')
def get_push_data():
    # 获取参数，设置默认值为当前日期
    start_date = request.args.get('start_date', datetime.now().strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    authors = request.args.getlist('authors[]')
    projects = request.args.getlist('projects[]')
    
    try:
        # 转换时间戳
        start_ts = pd.to_datetime(start_date).timestamp()
        end_ts = pd.to_datetime(end_date).timestamp() + 86399  # 包含当天23:59:59

        # 查询 Push 数据
        push_df = ReviewService().get_push_review_logs(
            authors=authors if authors else None,
            project_names=projects if projects else None,
            updated_at_gte=start_ts,
            updated_at_lte=end_ts
        )

        # 添加类型标记
        push_df['type'] = 'Push'
        push_df['target_branch'] = None
        push_df['source_branch'] = None
        push_df['url'] = None

        # 确保所有必需的字段都存在
        required_columns = ['project_name', 'author', 'branch', 'updated_at', 'commit_messages', 'score']
        for col in required_columns:
            if col not in push_df.columns:
                push_df[col] = None

        return push_df.to_json(orient='records')
    except Exception as e:
        logger.error(f"Error in get_push_data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_app.route('/api/mr-logs')
def get_mr_data():
    # 获取参数，设置默认值为当前日期
    start_date = request.args.get('start_date', datetime.now().strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    authors = request.args.getlist('authors[]')
    projects = request.args.getlist('projects[]')
    
    try:
        # 转换时间戳
        start_ts = pd.to_datetime(start_date).timestamp()
        end_ts = pd.to_datetime(end_date).timestamp() + 86399  # 包含当天23:59:59

        # 查询 MR 数据
        mr_df = ReviewService().get_mr_review_logs(
            authors=authors if authors else None,
            project_names=projects if projects else None,
            updated_at_gte=start_ts,
            updated_at_lte=end_ts
        )

        # 添加类型标记
        mr_df['type'] = 'MR'
        mr_df['branch'] = None  # 为 MR 添加 branch 字段，保持与 Push 数据结构一致

        # 确保所有必需的字段都存在
        required_columns = ['project_name', 'author', 'source_branch', 'target_branch', 'updated_at', 'commit_messages', 'score', 'url']
        for col in required_columns:
            if col not in mr_df.columns:
                mr_df[col] = None

        return mr_df.to_json(orient='records')
    except Exception as e:
        logger.error(f"Error in get_mr_data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_app.route('/api/config', methods=['GET'])
def get_config():
    """
    获取当前配置的API端点
    """
    if not session.get('authenticated'):
        return jsonify({'message': '未授权访问'}), 401
        
    try:
        # 读取当前.env文件内容
        env_path = find_dotenv("conf/.env")
        config = {}
        config_order = []  # 用于保存配置项的顺序
        
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    config[key] = value
                    config_order.append(key)  # 保存配置项的顺序
                    
        # 创建一个有序的配置对象
        ordered_config = {
            'config': config,
            'order': config_order
        }
        return jsonify(ordered_config)
    except Exception as e:
        logger.error(f"Failed to read config: {str(e)}")
        return jsonify({'message': '读取配置失败'}), 500

@api_app.route('/api/save-config', methods=['POST'])
def save_config():
    """
    保存配置的API端点
    """
    if not session.get('authenticated'):
        return jsonify({'message': '未授权访问'}), 401
        
    try:
        config = request.get_json()
        if not config:
            return jsonify({'message': '无效的配置数据'}), 400
            
        # 读取当前.env文件内容
        env_path = find_dotenv("conf/.env")
        lines = []
        config_dict = {}
        
        # 读取并解析现有配置
        with open(env_path, 'r', encoding='utf-8', newline='') as f:
            for line in f:
                # 保留原始行，包括注释和空行，保持原有换行符
                lines.append(line)
                # 如果是配置项，解析键值对
                if line.strip() and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config_dict[key.strip()] = value.strip()
        
        # 更新配置
        config_dict.update(config)
        
        # 构建新的配置文件内容
        new_content = []
        for line in lines:
            if line.strip() and not line.startswith('#'):
                # 如果是配置项，替换为新值
                key = line.split('=', 1)[0].strip()
                if key in config_dict:
                    new_content.append(f"{key}={config_dict[key]}\n")
                else:
                    # 删除不存在的配置项
                    continue
            else:
                # 保留注释和空行
                new_content.append(line)
        
        # 写入新的配置文件，保持原有换行符
        with open(env_path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(new_content)
                
        logger.info("Successfully saved config")
        
        # 重新加载配置
        if reload_env():
            return jsonify({'message': '配置保存并重新加载成功'})
        else:
            return jsonify({'message': '配置保存成功但重新加载失败'}), 500
            
    except Exception as e:
        logger.error(f"Failed to save config: {str(e)}")
        return jsonify({'message': '保存配置失败'}), 500

@api_app.route('/api/delete-config', methods=['POST'])
def delete_config():
    """
    删除配置项的API端点
    """
    if not session.get('authenticated'):
        return jsonify({'message': '未授权访问'}), 401
        
    try:
        data = request.get_json()
        if not data or 'key' not in data:
            return jsonify({'message': '无效的配置数据'}), 400
            
        key_to_delete = data['key']
            
        # 读取当前.env文件内容
        env_path = find_dotenv("conf/.env")
        lines = []
        config_dict = {}
        config_order = []  # 用于保存配置项的顺序
        
        # 读取并解析现有配置
        with open(env_path, 'r', encoding='utf-8', newline='') as f:
            for line in f:
                # 保留原始行，包括注释和空行，保持原有换行符
                lines.append(line)
                # 如果是配置项，解析键值对
                if line.strip() and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    config_dict[key] = value
                    config_order.append(key)  # 保存配置项的顺序
        
        # 删除指定的配置项
        if key_to_delete in config_dict:
            del config_dict[key_to_delete]
            # 从order数组中移除该key
            if key_to_delete in config_order:
                config_order.remove(key_to_delete)
        else:
            return jsonify({'message': '配置项不存在'}), 404
        
        # 构建新的配置文件内容
        new_content = []
        for line in lines:
            if line.strip() and not line.startswith('#'):
                # 如果是配置项，替换为新值
                key = line.split('=', 1)[0].strip()
                if key in config_dict:
                    new_content.append(f"{key}={config_dict[key]}\n")
                else:
                    # 删除不存在的配置项
                    continue
            else:
                # 保留注释和空行
                new_content.append(line)
        
        # 写入新的配置文件，保持原有换行符
        with open(env_path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(new_content)
                
        logger.info(f"Successfully deleted config key: {key_to_delete}")
        
        # 重新加载配置
        if reload_env():
            return jsonify({
                'message': '配置删除并重新加载成功',
                'config': config_dict,
                'order': config_order
            })
        else:
            return jsonify({'message': '配置删除成功但重新加载失败'}), 500
            
    except Exception as e:
        logger.error(f"Failed to delete config: {str(e)}")
        return jsonify({'message': '删除配置失败'}), 500

# 登录路由
@api_app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')
            
        if authenticate(username, password):
            session['authenticated'] = True
            return jsonify({'message': '登录成功'})
        else:
            return jsonify({'message': '用户名或密码错误'}), 401
    return render_template('login.html')

# 登出路由
@api_app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))

def authenticate(username, password):
    # 从环境变量读取凭证（与原 ui.py 逻辑一致）
    DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
    DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")
    return username == DASHBOARD_USER and password == DASHBOARD_PASSWORD

def reload_env():
    """
    重新加载.env文件并更新全局变量
    """
    try:
        # 重新加载.env文件
        load_dotenv(find_dotenv("conf/.env"), override=True)
        
        # 更新全局变量
        global PUSH_REVIEW_ENABLED
        PUSH_REVIEW_ENABLED = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'
        
        # 更新Flask secret key
        api_app.secret_key = os.getenv('FLASK_SECRET_KEY', 'ai123456789!!!')
        
        logger.info("Successfully reloaded .env file")
        return True
    except Exception as e:
        logger.error(f"Failed to reload .env file: {str(e)}")
        return False

@api_app.route('/api/reload-config', methods=['POST'])
def reload_config():
    """
    重新加载配置文件的API端点
    """
    if not session.get('authenticated'):
        return jsonify({'message': '未授权访问'}), 401
        
    if reload_env():
        return jsonify({'message': '配置重新加载成功'})
    else:
        return jsonify({'message': '配置重新加载失败'}), 500

@api_app.route('/api/chat', methods=['POST'])
def chat():
    """
    处理聊天请求的API端点，支持流式响应
    """
    if not session.get('authenticated'):
        return jsonify({'message': '未授权访问'}), 401
        
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'message': '无效的请求数据'}), 400
            
        message = data['message']
        system_message = data.get('system_message', '')
        user_message = data.get('user_message', '')
        use_context = data.get('use_context', False)  # 获取上下文开关参数，默认不启用
        
        def generate():
            try:
                # 获取 LLM 客户端
                client = Factory.getClient()
                
                # 构建消息
                messages = []
                if system_message:
                    messages.append({"role": "system", "content": system_message})
                
                # 如果提供了 user_message 模板，使用模板格式化消息
                if user_message:
                    formatted_message = user_message.format(message=message)
                else:
                    formatted_message = message
                    
                messages.append({"role": "user", "content": formatted_message})
                
                # 调用 LLM 客户端获取响应
                response = client.stream_completions(messages=messages)
                
                # 流式返回响应
                for chunk in response:
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                    time.sleep(0.05)  # 控制打字速度
                    
            except Exception as e:
                logger.error(f"LLM API error: {str(e)}")
                yield f"data: {json.dumps({'content': '抱歉，AI 服务出现错误，请稍后重试。'})}\n\n"
                
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        logger.error(f"Chat API error: {str(e)}")
        return jsonify({'message': '处理请求时发生错误'}), 500

@api_app.route('/api/agents', methods=['POST'])
def create_agent():
    """创建新的Agent"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Invalid data'}), 400
            
        agent_name = data['name']
        description = data.get('description', '')
        
        # 验证agent名称格式
        if not re.match(r'^[a-zA-Z0-9_-]+$', agent_name):
            return jsonify({'error': 'Agent名称只能包含字母、数字、下划线和连字符'}), 400
            
        # 检查agent是否已存在
        agent_dir = os.path.join('conf', 'agents', agent_name)
        if os.path.exists(agent_dir):
            return jsonify({'error': 'Agent已存在'}), 400
            
        # 创建agent目录
        os.makedirs(agent_dir, exist_ok=True)
        
        # 创建配置文件
        config_file = os.path.join(agent_dir, 'config.yml')
        config = {
            'name': agent_name,
            'description': description,
            'created_at': datetime.now().isoformat()
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
            
        # 创建空的提示词模板文件
        prompt_file = get_agent_prompt_file(agent_name)
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write('# Agent提示词模板\n')
            
        return jsonify({'message': 'Agent创建成功'})
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        return jsonify({'error': '创建Agent失败'}), 500

@api_app.route('/api/agents/<agent>', methods=['DELETE'])
def delete_agent(agent):
    """删除指定的Agent"""
    try:
        # 不允许删除default agent
        if agent == 'default':
            return jsonify({'error': '不能删除默认Agent'}), 400
            
        agent_dir = os.path.join('conf', 'agents', agent)
        if not os.path.exists(agent_dir):
            return jsonify({'error': 'Agent不存在'}), 404
            
        # 删除agent目录及其所有内容
        import shutil
        shutil.rmtree(agent_dir)
        
        return jsonify({'message': 'Agent删除成功'})
    except Exception as e:
        logger.error(f"Error deleting agent: {str(e)}")
        return jsonify({'error': '删除Agent失败'}), 500

if __name__ == '__main__':
    # 启动定时任务调度器
    setup_scheduler()

    # 启动Flask API服务
    port = int(os.environ.get('SERVER_PORT', 5001))
    api_app.run(host='0.0.0.0', port=port)
