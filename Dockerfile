# 使用官方的 Python 基础镜像
FROM python:3.10-slim AS base

# 设置工作目录
WORKDIR /app

# 安装 supervisord 作为进程管理工具
RUN apt-get update && apt-get install -y --no-install-recommends supervisor && rm -rf /var/lib/apt/lists/*

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

# 使用 supervisord 作为启动命令
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

FROM base AS app
COPY conf/supervisord.app.conf /etc/supervisor/conf.d/supervisord.conf
# 暴露 Flask 和 Streamlit 的端口
EXPOSE 5001 5002

FROM base AS worker
COPY ./conf/supervisord.worker.conf /etc/supervisor/conf.d/supervisord.conf