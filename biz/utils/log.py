import logging
import os
from logging.handlers import RotatingFileHandler

# 自定义 Logger 类，重写 warn 和 error 方法
class CustomLogger(logging.Logger):
    def warn(self, msg, *args, **kwargs):
        # 在 warn 消息前添加 ⚠️
        msg_with_emoji = f"⚠️ {msg}"
        super().warning(msg_with_emoji, *args, **kwargs)  # 注意：warn 是 warning 的别名

    def error(self, msg, *args, **kwargs):
        # 在 error 消息前添加 ❌
        msg_with_emoji = f"❌ {msg}"
        super().error(msg_with_emoji, *args, **kwargs)


log_file = os.environ.get("LOG_FILE", "log/app.log")
log_max_bytes = int(os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024))  # 默认10MB
log_backup_count = int(os.environ.get("LOG_BACKUP_COUNT", 5))  # 默认保留5个备份文件
# 设置日志级别
log_level = os.environ.get("LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, log_level.upper(), logging.INFO)

file_handler = RotatingFileHandler(
    filename=log_file,
    mode='a',
    maxBytes=log_max_bytes,
    backupCount=log_backup_count,
    encoding='utf-8',
    delay=False
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s'))
file_handler.setLevel(LOG_LEVEL)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s'))
console_handler.setLevel(LOG_LEVEL)


# 使用自定义的 Logger 类
logger = CustomLogger(__name__)
logger.setLevel(LOG_LEVEL)  # 设置 Logger 的日志级别
logger.addHandler(file_handler)
logger.addHandler(console_handler)
