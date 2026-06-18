# 使用官方的 Python 基础镜像
FROM python:3.10-slim AS app

# 设置工作目录
WORKDIR /app

# 安装系统依赖:
#   supervisor          - 进程管理
#   git                 - code-review-expert skill 依赖 git diff 界定改动范围
#   curl / ca-certificates - 安装 Node 及网络访问
#   nodejs + claude CLI - 运行 agentic skill 的运行时(Linux 下无需 git-bash)
RUN apt-get update && apt-get install -y --no-install-recommends \
        supervisor git curl ca-certificates gosu \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && claude --version \
    && npm cache clean --force \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件&创建必要的文件夹
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p log data conf
COPY biz ./biz
COPY fonts ./fonts
COPY api.py ./api.py
COPY ui.py ./ui.py
COPY conf/prompt_templates.yml ./conf/prompt_templates.yml
COPY conf/skills ./conf/skills
COPY conf/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY conf/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# 创建非 root 运行用户(claude CLI 需要可写的 HOME 来存放配置)
RUN useradd -m -u 1000 appuser \
    && chmod +x /usr/local/bin/docker-entrypoint.sh \
    && chown -R appuser:appuser /app
ENV HOME=/home/appuser

# 暴露 Flask 和 Streamlit 的端口
EXPOSE 5001 5002

# entrypoint 以 root 修正挂载目录权限后用 gosu 降权到 appuser 运行 supervisord
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]