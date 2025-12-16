# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 开发命令

### Docker 开发
```bash
# 启动所有服务
docker-compose up -d

# 停止服务
docker-compose stop

# 查看服务状态
docker-compose ps

# 重启服务
docker-compose restart

# 清理容器
docker-compose rm
```

### 本地开发
```bash
# 启动 Flask API 服务器（端口 5001）
python api.py

# 启动 Streamlit 仪表板（端口 5002）
streamlit run ui.py --server.port=5002 --server.address=0.0.0.0
```

### 测试
```bash
# 运行所有测试
python -m unittest discover -s test -p "test_*.py" -v

# 运行特定模块测试
python -m unittest test.biz.queue.test_whitelist -v
```

### 代码库审查工具
```bash
# 交互式完整代码库审查
python -m biz.cmd.review
```

## 架构概览

### 核心组件
- **Flask API 服务器** (`api.py`)：处理 GitLab/GitHub webhook 和审查请求
- **Streamlit 仪表板** (`ui.py`)：审查统计和日志的可视化界面
- **多容器部署**：Supervisor 管理的进程，使用 Redis Queue 进行异步处理

### 业务逻辑结构 (`biz/`)
- **`cmd/`**：不同审查功能的命令处理器
  - `review.py`：主要审查命令编排器
  - `func/`：专门的审查功能（分支、复杂度、目录、MySQL 审查）
- **`gitlab/`** 和 **`github/`**：平台特定的 webhook 处理器和 API 集成
- **`llm/`**：多 LLM 客户端实现，支持 DeepSeek、智谱AI、OpenAI、通义千问和 Ollama
- **`queue/`**：使用 Redis Queue worker 的异步作业处理
- **`service/`**：核心业务服务和审查编排
- **`utils/`**：日志、配置、即时消息通知和报告的实用工具
- **`entity/`**：数据模型和实体

### 配置系统
多级配置，优先级：**项目 > 命名空间 > 全局**
- 全局配置：`conf/.env`
- 命名空间级：`conf/{namespace}/.env`
- 项目级：`conf/{namespace}/{project_name}/.env`

### 数据库选项
- **SQLite**（默认）：`data/data.db` - 适合小团队
- **MySQL**：通过环境配置，适合大型部署

## 关键开发模式

### 事件驱动的 Webhook 处理
1. GitLab/GitHub 发送 webhook 事件到 Flask API (`/review/webhook`)
2. 事件通过 Redis Queue 排队进行异步处理
3. Worker 进程处理不同事件类型（合并请求、推送）
4. LLM 集成生成代码审查内容
5. 结果发布回 GitLab/GitHub 并通过即时消息通知发送

### 多 LLM 集成
- 支持 5 个 LLM 提供商的统一接口
- 可按项目/命名空间配置
- Token 管理和响应解析
- 不同的审查风格：专业、讽刺、温和、幽默

### 即时消息通知系统
- **钉钉**：Markdown 消息
- **企业微信**：文本消息支持@提及（推送事件）或 markdown
- **飞书**：应用消息
- **自定义 webhook**：用于扩展性

### 审查控制机制
- **白名单系统**：命名空间和项目级过滤
- **提交消息过滤**：基于正则表达式的触发控制
- **受保护分支过滤**：可选的审查限制
- **文件类型过滤**：可配置的支持扩展名

## 环境配置

复制 `conf/.env.dist` 到 `conf/.env` 并配置：
- LLM 提供商设置（选择一个：deepseek, openai, zhipuai, qwen, ollama）
- GitLab/GitHub 访问令牌
- 即时消息 webhook URL（可选）
- 数据库设置（SQLite/MySQL）
- 审查行为选项（风格、限制、过滤器）

## 端口配置
- **Flask API**：5001
- **Streamlit 仪表板**：5002
- **Ollama**：11434（如果外部使用）

## 测试结构
测试文件镜像 `biz/` 目录结构：
- `test/biz/gitlab/test_webhook_handler.py`：Webhook 处理测试
- `test/biz/queue/test_whitelist_isolation.py`：配置过滤测试
- 基于 pytest 的全面测试，包含 64+ 个测试文件

## 生产部署
- 多阶段 Docker 构建，使用 supervisor 进程管理
- 分离的应用和 worker 容器目标
- 持久数据、日志和配置的卷挂载
- 健康检查和自动重启策略