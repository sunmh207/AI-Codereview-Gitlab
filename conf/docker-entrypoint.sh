#!/bin/sh
set -e

APP_USER=appuser
APP_HOME=/home/appuser

# 确保挂载目录(bind mount 会带宿主机属主)与 claude 配置目录存在且归属非 root 用户，
# 否则非 root 进程无法写入 log/data 或 claude 配置(~/.claude)。
mkdir -p /app/log /app/data "$APP_HOME/.claude"
chown -R "$APP_USER":"$APP_USER" /app/log /app/data "$APP_HOME" 2>/dev/null || true

# supervisord(PID1) 以 root 运行，以便能打开 /dev/stdout、/dev/stderr 写日志；
# 实际的 flask/streamlit/claude 进程由 supervisord 通过 user=appuser 降权运行(见 supervisord.conf)。
exec "$@"
