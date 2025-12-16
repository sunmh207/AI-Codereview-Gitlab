import ast
import os
import re
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN
from biz.utils.log import logger


class ClaudeCodeClient(BaseClient):
    """Claude Code LLM 客户端,通过 subprocess 调用 Claude Code CLI"""

    def __init__(self, api_key: str = None):
        """
        初始化 Claude Code 客户端

        Args:
            api_key: Anthropic API 密钥,如果未提供则从环境变量读取

        Raises:
            ValueError: 当 API 密钥未配置时
            RuntimeError: 当 Claude Code CLI 未安装时
        """
        self.api_key = api_key or os.getenv("CLAUDE_CODE_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set CLAUDE_CODE_API_KEY in the environment variables.")

        self.base_url = os.getenv("CLAUDE_CODE_API_BASE_URL", "https://api.anthropic.com")
        self.default_model = os.getenv("CLAUDE_CODE_API_MODEL", "sonnet")
        self.cli_path = os.getenv("CLAUDE_CODE_CLI_PATH", "claude")

        # 检查 Claude CLI 是否已安装
        if not self._check_cli_installed():
            raise RuntimeError(
                "Claude Code CLI 未安装,请运行: npm install -g @anthropic-ai/claude-code"
            )

        logger.info(f"ClaudeCodeClient initialized with model: {self.default_model}, base_url: {self.base_url}")

    def _check_cli_installed(self) -> bool:
        """
        检查 Claude Code CLI 是否已安装

        Returns:
            已安装返回 True,否则返回 False
        """
        cli_path = shutil.which(self.cli_path)
        if cli_path:
            logger.debug(f"Claude CLI found at: {cli_path}")
            return True
        else:
            logger.error(f"Claude CLI not found in PATH: {self.cli_path}")
            return False

    def _format_dict_to_readable(self, data: dict) -> str:
        """
        将字典转换为可读的 key-value 字符串格式

        Args:
            data: 字典数据

        Returns:
            格式化后的字符串
        """
        # 定义字段顺序（优先显示的字段）
        priority_keys = ['diff', 'new_path', 'old_path', 'new_file', 'renamed_file', 'deleted_file']
        result_parts = []

        # 按优先级处理字段
        for key in priority_keys:
            if key in data:
                value = data[key]
                result_parts.append(f"{key}:\n{value}\n")

        # 处理其他未在优先级列表中的字段
        for key, value in data.items():
            if key not in priority_keys:
                result_parts.append(f"{key}:\n{value}\n")

        return "\n".join(result_parts)

    def _format_list_in_string(self, content: str) -> str:
        """
        查找字符串中的 Python 列表表示并格式化

        Args:
            content: 可能包含列表字面量的字符串

        Returns:
            格式化后的字符串
        """
        def find_list_literals(text: str) -> list:
            """查找字符串中所有的列表字面量，返回 (start, end, list_obj) 列表"""
            results = []
            i = 0

            while i < len(text):
                if text[i] == '[':
                    # 尝试从这个位置开始解析列表
                    # 使用栈来找到匹配的结束括号
                    brackets = []  # 跟踪 []
                    braces = []    # 跟踪 {}
                    in_string = False
                    escape_next = False
                    j = i

                    while j < len(text):
                        char = text[j]

                        if escape_next:
                            escape_next = False
                            j += 1
                            continue

                        if char == '\\':
                            escape_next = True
                            j += 1
                            continue

                        if char == '"' or char == "'":
                            in_string = not in_string
                        elif not in_string:
                            if char == '[':
                                brackets.append('[')
                            elif char == ']':
                                if brackets:
                                    brackets.pop()
                                    if not brackets:
                                        # 找到匹配的结束括号
                                        list_str = text[i:j+1]
                                        try:
                                            list_obj = ast.literal_eval(list_str)
                                            # 只处理包含字典的列表
                                            if isinstance(list_obj, list) and list_obj and any(isinstance(item, dict) for item in list_obj):
                                                results.append((i, j+1, list_obj))
                                        except (SyntaxError, ValueError):
                                            pass
                                        break
                            elif char == '{':
                                braces.append('{')
                            elif char == '}':
                                if braces:
                                    braces.pop()

                        j += 1
                i += 1

            return results

        # 查找所有列表字面量
        list_literals = find_list_literals(content)

        if not list_literals:
            return content

        # 从后往前替换，避免位置偏移问题
        result = content
        for start, end, list_obj in reversed(list_literals):
            # 格式化列表中的每个字典
            formatted_items = []
            for i, item in enumerate(list_obj, 1):
                if isinstance(item, dict):
                    formatted = self._format_dict_to_readable(item)
                    # 添加分隔符
                    if i > 1:
                        formatted_items.append("\n" + "=" * 80 + "\n")
                    formatted_items.append(formatted)
                else:
                    # 如果不是字典，保持原样
                    formatted_items.append(str(item))

            formatted_str = "\n".join(formatted_items)
            result = result[:start] + formatted_str + result[end:]

        return result

    def _format_messages(self, messages: List[Dict[str, str]]) -> tuple[str, str]:
        """
        将消息列表格式化为 Claude Code CLI 可接受的提示文本

        Args:
            messages: 消息列表

        Returns:
            格式化后的提示文本元组 (user_content, system_content)
        """
        # 分别收集 user 和 system 消息
        user_parts = []
        system_parts = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            if role == "user":
                logger.debug(f"context 的类型为: {type(content)}")
                # 处理 content：支持字典和字符串两种类型
                if isinstance(content, dict):
                    # 字典类型：直接格式化
                    content = self._format_dict_to_readable(content)
                elif isinstance(content, str):
                    # 字符串类型：查找并格式化其中的列表
                    content = self._format_list_in_string(content)
                user_parts.append(content)
            elif role == "system":
                system_parts.append(content)

        # 合并所有消息内容
        user_content = "\n\n".join(user_parts)
        system_content = "\n\n".join(system_parts)

        logger.debug(f"Formatted {len(messages)} messages: user_content length={len(user_content)}, system_content length={len(system_content)}")

        return user_content, system_content

    def _execute_claude_command(self, user_content: str, system_content: str, model: Optional[str] = None) -> str:
        """
        执行 Claude Code CLI 命令

        Args:
            user_content: 用户消息内容
            system_content: 系统提示内容
            model: 模型名称(sonnet/opus/haiku)

        Returns:
            命令的标准输出

        Raises:
            subprocess.CalledProcessError: 命令执行失败时
        """
        # 设置环境变量,传递 API 密钥和 Base URL
        env = os.environ.copy()
        env['ANTHROPIC_API_KEY'] = self.api_key
        env['ANTHROPIC_BASE_URL'] = self.base_url

        # 设置额外的环境变量(使用 CLAUDE_CODE_ENV_ 前缀的配置)
        env_mappings = {
            'CLAUDE_CODE_ENV_http_proxy': 'http_proxy',
            'CLAUDE_CODE_ENV_https_proxy': 'https_proxy',
            'CLAUDE_CODE_ENV_HTTP_PROXY': 'HTTP_PROXY',
            'CLAUDE_CODE_ENV_HTTPS_PROXY': 'HTTPS_PROXY',
            'CLAUDE_CODE_ENV_NODE_EXTRA_CA_CERTS': 'NODE_EXTRA_CA_CERTS',
        }

        for config_key, env_key in env_mappings.items():
            env_value = os.getenv(config_key)
            if env_value:
                env[env_key] = env_value
                logger.debug(f"Setting environment variable from {config_key}: {env_key}={env_value}")

        # 构建 prompt
        combined_prompt = f"{system_content}\n\n{user_content}"
        prompt_size_kb = len(combined_prompt.encode('utf-8')) / 1024

        # 获取 log 目录的绝对路径（从 LOG_FILE 环境变量提取目录）
        log_file = os.environ.get("LOG_FILE", "log/app.log")
        log_dir = os.path.abspath(os.path.dirname(log_file))
        os.makedirs(log_dir, exist_ok=True)

        # 创建临时文件（使用可读的时间戳格式）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 保留毫秒
        temp_filename = os.path.join(log_dir, f"claude_prompt_{timestamp}.txt")

        temp_file_created = False
        should_delete_temp = True
        try:
            # 写入 prompt 到临时文件
            with open(temp_filename, 'w', encoding='utf-8') as f:
                f.write(combined_prompt)
            temp_file_created = True

            logger.debug(f"Created temp file: {temp_filename}")

            # 构建 shell 管道命令: cat temp_file | claude -p --model xxx
            cmd = f"cat {temp_filename} | {self.cli_path} -p --permission-mode acceptEdits --allowedTools \"Bash(*) Read(*) Edit(*) Write(*)\" --debug"
            if model:
                cmd += f" --model {model}"

            logger.debug(f"Executing Claude CLI command (model: {model or 'default'}, prompt size: {prompt_size_kb:.2f} KB)")
            logger.debug(f"Shell command: {cmd}")

            # 执行命令（使用 shell=True 支持管道）
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600,  # 10分钟超时
                env=env
            )

            # 记录 stderr（如果有，可能包含警告信息）
            if result.stderr:
                logger.warning(f"Claude CLI stderr: {result.stderr}")

            # 检查返回码
            if result.returncode != 0:
                logger.error(f"Claude CLI failed with return code {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                should_delete_temp = False  # 出错时保留临时文件
                logger.error(f"Temp file preserved for debugging: {temp_filename}")
                raise subprocess.CalledProcessError(
                    result.returncode,
                    cmd,
                    result.stdout,
                    result.stderr
                )

            # 记录成功信息
            logger.debug(f"Claude CLI execution successful, output length: {len(result.stdout)} chars")

            # 如果输出为空或只有空白字符，记录更详细的信息
            if not result.stdout or not result.stdout.strip():
                logger.error(f"Claude CLI returned empty output. Command: {cmd}")
                logger.error(f"Return code: {result.returncode}")
                logger.error(f"STDERR: {result.stderr}")
                # 记录输出的十六进制表示，帮助诊断问题
                if result.stdout:
                    logger.error(f"STDOUT hex: {result.stdout.encode('utf-8').hex()}")
                    logger.error(f"STDOUT repr: {repr(result.stdout)}")
                # 出错时保留临时文件
                should_delete_temp = False
                logger.error(f"Temp file preserved for debugging: {temp_filename}")

            return result.stdout

        finally:
            # 清理临时文件（仅在没有错误时删除）
            if temp_file_created and should_delete_temp and os.path.exists(temp_filename):
                try:
                    os.unlink(temp_filename)
                    logger.debug(f"Deleted temp file: {temp_filename}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_filename}: {e}")

    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN) -> str:
        """
        调用 Claude Code CLI 进行代码审查

        Args:
            messages: 消息列表,格式为 [{"role": "user", "content": "..."}]
            model: 模型名称,如果未提供则使用默认模型

        Returns:
            Claude Code CLI 返回的文本内容

        Raises:
            Exception: CLI 调用失败时
        """
        try:
            # 使用默认模型或指定模型
            model = model or self.default_model

            # 格式化消息
            user_content, system_content = self._format_messages(messages)

            logger.debug(f"Calling Claude Code CLI. Model: {model}, User content length: {len(user_content)}, System content length: {len(system_content)}")

            # 执行 Claude CLI 命令
            result = self._execute_claude_command(user_content, system_content, model)

            # 处理空响应
            if not result or not result.strip():
                logger.error("Empty response from Claude Code CLI")
                return "Claude Code 返回为空,请稍后重试"

            # 返回结果(去除多余空格)
            return result.strip()

        except subprocess.TimeoutExpired:
            logger.error("Claude Code CLI timeout")
            return "Claude Code 执行超时,请稍后重试或检查代码大小"

        except subprocess.CalledProcessError as e:
            logger.error(f"Claude Code CLI error: {e.stderr}", exc_info=True)
            stderr = str(e.stderr).lower() if e.stderr else ""

            # 根据错误信息返回友好提示
            if "authentication" in stderr or "api key" in stderr:
                return "Claude Code 认证失败,请检查 ANTHROPIC_API_KEY 是否正确配置"
            elif "model" in stderr:
                return "Claude Code 模型配置错误,请使用 sonnet/opus/haiku"
            elif "rate limit" in stderr:
                return "Claude Code 请求过于频繁,请稍后重试"
            else:
                return f"Claude Code 执行失败: {e.stderr}"

        except Exception as e:
            logger.error(f"Claude Code error: {str(e)}", exc_info=True)
            return f"调用 Claude Code 时出错: {str(e)}"

    def ping(self) -> bool:
        """
        测试与 Claude Code CLI 的连接

        Returns:
            连接成功返回 True,否则返回 False
        """
        try:
            # 发送简单测试消息
            result = self.completions(messages=[{"role": "user", "content": '请仅返回 "ok"。'}])

            # 检查返回结果
            if result and result.strip().lower() == "ok":
                logger.info("Claude Code CLI connection test successful")
                return True
            else:
                logger.warning(f"Claude Code CLI connection test returned unexpected result: {result}")
                return False

        except Exception as e:
            logger.error(f"Claude Code CLI connection test failed: {str(e)}")
            return False
