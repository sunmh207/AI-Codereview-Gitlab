"""
错误处理模块 - 统一处理和格式化错误通知
"""
import traceback
import json
from datetime import datetime
from typing import Optional, Callable, Any


class ErrorClassifier:
    """错误分类器"""

    @classmethod
    def classify(cls, exception: Exception) -> tuple[str, str]:
        """
        返回 (error_type, severity)

        Args:
            exception: 异常对象

        Returns:
            (错误类型, 严重级别) 元组
        """
        # 导入可能不存在的模块
        try:
            import requests
            network_errors = (requests.ConnectionError, requests.Timeout)
        except ImportError:
            network_errors = ()

        try:
            import openai
            api_errors = (
                openai.APIError,
                openai.APIConnectionError,
                openai.RateLimitError,
                openai.InternalServerError,
                openai.AuthenticationError,
            )
        except ImportError:
            api_errors = ()

        # 网络错误
        if isinstance(exception, network_errors):
            return ('NETWORK', 'HIGH')

        # OpenAI API错误
        if isinstance(exception, api_errors):
            return ('API', 'HIGH')

        # 从错误消息中判断
        error_str = str(exception)

        # API错误（通过状态码）
        if any(code in error_str for code in ['500', '502', '503']):
            return ('API', 'HIGH')
        if any(code in error_str for code in ['401', '403']):
            return ('API', 'CRITICAL')

        # 配置错误
        if isinstance(exception, (ValueError, KeyError)):
            if any(keyword in error_str for keyword in ['WEBHOOK', 'TOKEN', 'API_KEY', 'SECRET', '环境变量']):
                return ('CONFIG', 'CRITICAL')

        # 业务错误（代码审查相关）
        if 'CodeReview' in error_str or 'review' in error_str.lower():
            return ('BUSINESS', 'MEDIUM')

        return ('UNKNOWN', 'MEDIUM')

    @classmethod
    def get_type_name(cls, error_type: str) -> str:
        """获取错误类型的中文显示名称"""
        type_names = {
            'NETWORK': '网络错误',
            'API': 'API错误',
            'CONFIG': '配置错误',
            'BUSINESS': '业务错误',
            'UNKNOWN': '未知错误'
        }
        return type_names.get(error_type, '未知')

    @classmethod
    def extract_context(cls, webhook_data: Optional[dict], function_name: str) -> dict:
        """
        从webhook数据提取上下文信息

        Args:
            webhook_data: webhook数据
            function_name: 函数名

        Returns:
            上下文字典
        """
        context = {
            'function': function_name,
            'platform': 'unknown',
        }

        if not webhook_data:
            return context

        # GitLab
        if 'project' in webhook_data and isinstance(webhook_data.get('project'), dict):
            context['project'] = webhook_data['project'].get('name', 'unknown')
            context['platform'] = 'GitLab'
            if 'user' in webhook_data:
                context['author'] = webhook_data['user'].get('username', 'unknown')

        # GitHub / Gitea
        elif 'repository' in webhook_data and isinstance(webhook_data.get('repository'), dict):
            context['project'] = webhook_data['repository'].get('name', 'unknown')
            context['platform'] = 'GitHub' if 'sender' in webhook_data else 'Gitea'
            if 'sender' in webhook_data:
                context['author'] = webhook_data['sender'].get('login', 'unknown')

        # 操作描述
        operation_map = {
            'handle_push_event': '处理Push事件',
            'handle_merge_request_event': '处理Merge Request事件',
            'handle_github_push_event': '处理GitHub Push事件',
            'handle_github_pull_request_event': '处理GitHub Pull Request事件',
            'handle_gitea_push_event': '处理Gitea Push事件',
            'handle_gitea_pull_request_event': '处理Gitea Pull Request事件',
        }
        context['operation'] = operation_map.get(function_name, function_name)

        return context


class ErrorFormatter:
    """错误消息格式化器"""

    MAX_IM_LENGTH = 2000

    @staticmethod
    def format_for_im(exception: Exception, error_type: str,
                     severity: str, context: dict) -> str:
        """
        生成IM通知的简洁错误消息

        Args:
            exception: 异常对象
            error_type: 错误类型
            severity: 严重级别
            context: 上下文字典

        Returns:
            格式化后的IM消息
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        lines = [
            "【AI Code Review 错误通知】",
            "━━━━━━━━━━━━━━━━━━━━",
            f"类型: {ErrorClassifier.get_type_name(error_type)}",
            f"级别: {severity}",
            f"时间: {timestamp}",
            "",
            str(exception)[:200],  # 限制异常消息长度
            "",
        ]

        # 添加上下文信息
        if context.get('project'):
            lines.append(f"项目: {context['project']}")
        if context.get('platform'):
            lines.append(f"平台: {context['platform']}")
        if context.get('operation'):
            lines.append(f"操作: {context['operation']}")
        if context.get('author'):
            lines.append(f"操作用户: {context['author']}")

        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "详细日志已记录到系统，请联系管理员查看"
        ])

        message = '\n'.join(lines)

        # 确保不超过最大长度
        if len(message) > ErrorFormatter.MAX_IM_LENGTH:
            message = message[:ErrorFormatter.MAX_IM_LENGTH-3] + '...'

        return message

    @staticmethod
    def format_for_log(exception: Exception, error_type: str,
                      severity: str, context: dict) -> str:
        """
        生成日志的完整错误信息（包含堆栈）

        Args:
            exception: 异常对象
            error_type: 错误类型
            severity: 严重级别
            context: 上下文字典

        Returns:
            格式化后的日志消息
        """
        context_str = json.dumps(context, ensure_ascii=False, indent=2)

        return f'''【错误详情】
类型: {error_type}
级别: {severity}
异常类: {type(exception).__name__}
异常消息: {str(exception)}

【上下文信息】
{context_str}

【堆栈跟踪】
{traceback.format_exc()}
'''


class ErrorHandler:
    """统一错误处理接口"""

    @staticmethod
    def handle_error(exception: Exception,
                    function_name: str,
                    webhook_data: Optional[dict] = None,
                    logger_instance: Optional[Any] = None,
                    notifier_instance: Optional[Callable] = None):
        """
        统一错误处理入口

        Args:
            exception: 捕获的异常
            function_name: 出错的函数名
            webhook_data: webhook数据（用于提取上下文）
            logger_instance: 日志器（默认使用全局logger）
            notifier_instance: 通知器（默认使用全局send_notification函数）
        """
        # 延迟导入避免循环依赖
        from biz.utils.log import logger
        from biz.utils.im.notifier import send_notification

        logger_instance = logger_instance or logger
        notifier_instance = notifier_instance or send_notification

        # 1. 分类错误
        error_type, severity = ErrorClassifier.classify(exception)

        # 2. 提取上下文
        context = ErrorClassifier.extract_context(webhook_data, function_name)

        # 3. 生成并发送IM通知
        im_message = ErrorFormatter.format_for_im(
            exception, error_type, severity, context
        )
        notifier_instance(content=im_message)

        # 4. 记录完整日志
        log_message = ErrorFormatter.format_for_log(
            exception, error_type, severity, context
        )
        logger_instance.error(log_message)
