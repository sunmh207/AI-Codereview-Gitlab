import atexit
import json
import os
import traceback
from datetime import datetime
from multiprocessing import Process

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from flask import Flask, request, jsonify

from biz.ai.code_reviewer import CodeReviewer
from biz.ai.reporter import Reporter
from biz.gitlab.webhook_handler import MergeRequestHandler, PushHandler
from biz.utils.dingtalk import DingTalkNotifier
from biz.utils.feishu import FeishuNotifier
from biz.utils.log import logger
from biz.utils.wecom import WeComNotifier

load_dotenv()
app = Flask(__name__)


@app.route('/review/daily_report', methods=['GET'])
def daily_report():
    data_dir = os.getenv('REPORT_DATA_DIR', './')
    data_file = "push_" + datetime.now().strftime("%Y-%m-%d") + ".json"
    data_file_path = os.path.join(data_dir, data_file)
    data_entries = []
    if os.path.exists(data_file_path):
        with open(data_file_path, 'r', encoding='utf-8') as file:
            for line in file:
                # 解析每一行的 JSON 内容，并添加到 data_entries 数组中
                try:
                    data_entries.append(json.loads(line))
                except json.JSONDecodeError:
                    # 处理可能的 JSON 解码错误
                    logger.error(f"Skipping invalid JSON entry: {line}")
    else:
        logger.error(f"Log file {data_file_path} does not exist.")
        return jsonify({'message': f"Log file {data_file_path} does not exist."}), 404

    # 如果没有data,直接返回
    if not data_entries:
        return jsonify({'message': 'No data to process.'}), 200

    # 使用字典去重 (author, message) 相同的提交记录
    unique_commits = {}
    for entry in data_entries:
        author = entry.get("author", "Unknown Author")
        message = entry.get("message", "").strip()
        if (author, message) not in unique_commits:
            unique_commits[(author, message)] = {"author": author, "message": message}

    # 转换为列表形式，并按照 author 排序
    commits = sorted(unique_commits.values(), key=lambda x: x["author"])
    report_txt = Reporter().generate_report(json.dumps(commits))
    # 发钉钉消息
    send_notification(content=report_txt, msg_type="markdown", title="代码提交日报")
    return json.dumps(report_txt, ensure_ascii=False, indent=4)


# 启动定时生成日报的任务
scheduler = BackgroundScheduler()
crontab_expression = os.getenv('REPORT_CRONTAB_EXPRESSION', '0 21 * * 1-5')
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

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())


# 处理 GitLab Merge Request Webhook
@app.route('/review/webhook', methods=['POST'])
def handle_webhook():
    # 获取请求的JSON数据
    if request.is_json:
        data = request.get_json()
        event_type = request.headers.get('X-Gitlab-Event')

        # 优先从请求头获取，如果没有，则从环境变量获取
        gitlab_url = request.headers.get('X-Gitlab-Instance') or os.getenv('GITLAB_URL')
        gitlab_token = request.headers.get('X-Gitlab-Token')
        # 优先从环境变量获取，如果没有，则从请求头获取
        gitlab_token = os.getenv('GITLAB_ACCESS_TOKEN') or request.headers.get('X-Gitlab-Token')
        # 如果gitlab_token为空，返回错误
        if not gitlab_token:
            return jsonify({'message': 'Missing GitLab access token'}), 400

        # 打印整个payload数据，或根据需求进行处理
        logger.info(f'Received event: {event_type}')
        logger.info(f'Payload: {json.dumps(data)}')

        # 处理Merge Request Hook
        if event_type == 'Merge Request Hook':
            # 创建一个新进程进行异步处理
            process = Process(target=handle_merge_request_event, args=(data, gitlab_token, gitlab_url))
            process.start()
            # 立马返回响应
            return jsonify({'message': 'Request received, will process asynchronously.'}), 200
        elif event_type == 'Push Hook':
            # 创建一个新进程进行异步处理
            process = Process(target=handle_push_event, args=(data, gitlab_token, gitlab_url))
            process.start()
            # 立马返回响应
            return jsonify({'message': 'Request received, will process asynchronously.'}), 200
        else:
            return jsonify({'message': 'Event type not supported'}), 400
    else:
        return jsonify({'message': 'Invalid data format'}), 400


def handle_push_event(webhook_data: dict, gitlab_token: str, gitlab_url: str):
    try:
        handler = PushHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Push Hook event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return jsonify({'message': 'Failed to get commits'}), 500

        # 获取代码差异
        changes = handler.get_push_changes()
        if not changes:
            logger.info('未检测到有关代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            return jsonify({
                'message': 'No code modifications were detected, the modified file may not satisfy SUPPORTED_EXTENSIONS.'}), 500

        # 记录到数据文件中
        commits_filtered = [{'message': commit['message'], 'author': commit['author'], 'timestamp': commit['timestamp']}
                            for commit in commits]
        data_dir = os.getenv('REPORT_DATA_DIR', './')
        push_data_file = "push_" + datetime.now().strftime("%Y-%m-%d") + ".json"
        push_file_path = os.path.join(data_dir, push_data_file)
        with open(push_file_path, 'a', encoding='utf-8') as f:
            for commit in commits_filtered:
                f.write(json.dumps(commit, ensure_ascii=False) + "\n")

        # 进行代码审查
        commits_text = ';'.join(commit['message'] for commit in commits)
        review_result = review_code(str(filter_changes(changes)), commits_text)

        #添加异常处理，写入失败不要影响通知
        try:
            # 将审查结果添加到提交记录的评论中 
            handler.add_push_notes(f'Auto Review Result: {review_result}')
        except Exception as e:
            logger.error(f"Failed to add note: {e}")
       

        # 构建 Markdown 格式的钉钉消息
        dingtalk_msg = f"### 🚀 {webhook_data['project']['name']}: Push\n\n"
        dingtalk_msg += "#### 提交记录:\n"

        for commit in commits:
            message = commit.get('message', '').strip()
            # 从author字典中获取name
            author_name = commit.get('author', {}).get('name', 'Unknown Author')
            timestamp = commit.get('timestamp', '')
            url = commit.get('url', '#')

            dingtalk_msg += (
                f"- **提交信息**: {message}\n"
                f"- **提交者**: @{author_name}\n"
                f"- **时间**: {timestamp}\n"
                f"- [查看提交详情]({url})\n\n"
                f"- **AI Review 结果**: 👇👇👇👇👇👇👇👇\n"
                f"-  {review_result}\n\n"
            )

        send_notification(content=dingtalk_msg, msg_type='markdown',
                          title=f"{webhook_data['project']['name']} Push Event",
                          project={webhook_data['project']['name']})
    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        send_notification(error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_merge_request_event(webhook_data: dict, gitlab_token: str, gitlab_url: str):
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
            if not changes:
                logger.info('未检测到有关代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
                return jsonify({
                    'message': 'No code modifications were detected, the modified file may not satisfy SUPPORTED_EXTENSIONS.'}), 500
            # 获取Merge Request的commits
            commits = handler.get_merge_request_commits()
            if not commits:
                logger.error('Failed to get commits')
                return jsonify({'message': 'Failed to get commits'}), 500

            # review 代码
            commits_text = ';'.join(commit['title'] for commit in commits)
            review_result = review_code(str(filter_changes(changes)), commits_text)

            # 将review结果提交到Gitlab的 notes
            handler.add_merge_request_notes(f'Auto Review Result: {review_result}')

            # 构建 Markdown 格式的钉钉消息
            dingtalk_msg = f"### 🔀 {webhook_data['project']['name']}: Merge Request\n\n"
            dingtalk_msg += f"#### 合并请求信息:\n"

            dingtalk_msg += (
                f"- **提交者:** {webhook_data['user']['name']}\n\n"
                f"- **源分支**: `{webhook_data['object_attributes']['source_branch']}`\n"
                f"- **目标分支**: `{webhook_data['object_attributes']['target_branch']}`\n"
                f"- **更新时间**: {webhook_data['object_attributes']['updated_at']}\n"
                f"- **提交信息:** {commits_text}\n\n"
                f"- [查看合并详情]({webhook_data['object_attributes']['url']})\n\n"
                f"- **AI Review 结果**: 👇👇👇👇👇👇👇👇\n"
                f"-  {review_result}\n\n"
            )
            send_notification(content=dingtalk_msg, msg_type='markdown', 
                              title='Merge Request Review',
                              project={webhook_data['project']['name']})
        else:
            logger.info(f"Merge Request Hook event, action={handler.action}, ignored.")

    except Exception as e:
        error_message = f'AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        send_notification(error_message)
        logger.error('出现未知错误: %s', error_message)


def filter_changes(changes: list):
    '''
    过滤数据，只保留支持的文件类型以及必要的字段信息
    '''
    # 从环境变量中获取支持的文件扩展名
    SUPPORTED_EXTENSIONS = os.getenv('SUPPORTED_EXTENSIONS', '.java,.py,.php').split(',')
    # 过滤 `new_path` 以支持的扩展名结尾的元素, 仅保留diff和new_path字段
    filtered_changes = [
        {'diff': item['diff'], 'new_path': item['new_path']}
        for item in changes
        if any(item.get('new_path', '').endswith(ext) for ext in SUPPORTED_EXTENSIONS)
    ]
    return filtered_changes


# 分文件review代码
# def review_code(data: dict):
#     changes = data.get('changes', [])
#
#     # 如果超长，取前REVIEW_MAX_LENGTH字符
#     review_max_length = int(os.getenv('REVIEW_MAX_LENGTH', 5000))
#     review_result = []
#     # 如果changes为空,打印日志
#     if not changes:
#         logger.info('代码为空, data = %', str(data))
#         return '代码为空'
#
#     for change in changes:
#         new_path = change.get('new_path', '')
#         diff = change.get('diff', '')
#         parser = GitDiffParser(diff)
#
#         old_code = parser.get_old_code()
#         new_code = parser.get_new_code()
#
#         content = {
#             '文件名': new_path,
#             '修改前代码': old_code,
#             '修改后代码': new_code,
#         }
#         content_str = str(content)
#
#         if len(content_str) > review_max_length:
#             content_str = content_str[:review_max_length]
#             logger.info(f'文本超长，截段后content: {content_str}')
#
#         review_result.append(CodeReviewer().review_code(content_str))
#     return str(review_result)

# def review_code(data: dict):
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

    return CodeReviewer().review_code(changes_text, commits_text)


def send_notification(content, msg_type='text', title="通知", is_at_all=False,project=None):
    """
    发送通知消息到配置的平台(钉钉和企业微信)
    :param content: 消息内容
    :param msg_type: 消息类型，支持text和markdown
    :param title: 消息标题(markdown类型时使用)
    :param is_at_all: 是否@所有人
    """
    # 钉钉推送
    notifier = DingTalkNotifier(project_name = project)
    notifier.send_message(content=content, msg_type=msg_type, title=title, is_at_all=is_at_all)

    # 企业微信推送
    wecom_notifier = WeComNotifier()
    wecom_notifier.send_message(content=content, msg_type=msg_type, title=title, is_at_all=is_at_all)

    # 飞书推送
    feishu_notifier = FeishuNotifier()
    feishu_notifier.send_message(content=content, msg_type=msg_type, title=title, is_at_all=is_at_all)


if __name__ == '__main__':
    port = int(os.environ.get('SERVER_PORT', 5001))
    app.run(host='0.0.0.0', port=port)
