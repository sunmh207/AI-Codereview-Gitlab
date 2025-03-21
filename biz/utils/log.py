import logging
import os
from logging.handlers import RotatingFileHandler

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


logger = logging.Logger(__name__)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
