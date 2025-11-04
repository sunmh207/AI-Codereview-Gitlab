![Push图片](doc/img/open/ai-codereview-cartoon.png)

## 项目简介

本项目是一个基于大模型的自动化代码审查工具，帮助开发团队在代码合并或提交时，快速进行智能化的审查(Code Review)，提升代码质量和开发效率。

## 功能

- 🚀 多模型支持
  - 兼容 DeepSeek、ZhipuAI、OpenAI、通义千问 和 Ollama，想用哪个就用哪个。
- 📢 消息即时推送
  - 审查结果一键直达 钉钉、企业微信 或 飞书，代码问题无处可藏！
  - 🆕 **企微增强**：支持 text 消息格式，可 @commit 者，并展示 AI Review 评分和详情链接！
- 📅 自动化日报生成
  - 基于 GitLab & GitHub Commit 记录，自动整理每日开发进展，谁在摸鱼、谁在卷，一目了然 😼。
- 📊 可视化 Dashboard
  - 集中展示所有 Code Review 记录，项目统计、开发者统计，数据说话，甩锅无门！
- 🎭 Review Style 任你选
  - 专业型 🤵：严谨细致，正式专业。 
  - 讽刺型 😈：毒舌吐槽，专治不服（“这代码是用脚写的吗？”） 
  - 绅士型 🌸：温柔建议，如沐春风（“或许这里可以再优化一下呢~”） 
  - 幽默型 🤪：搞笑点评，快乐改码（“这段 if-else 比我的相亲经历还曲折！”）
- 🎯 **多级配置系统**
  - 支持项目级别、命名空间级别、全局配置，优先级：项目 > 命名空间 > 全局
  - 可为不同项目配置独立的 LLM、Review 风格、Prompt 模板等
- 🎯 **白名单控制**
  - 支持按命名空间或项目配置 Review 白名单，精准控制哪些项目允许进行代码审查
  - 支持 commit message 规则过滤，仅匹配特定 message 时才触发 Review

**效果图:**

![MR图片](doc/img/open/mr.png)

![Note图片](doc/img/open/note.jpg)

![Dashboard图片](doc/img/open/dashboard.jpg)

## 原理

当用户在 GitLab 上提交代码（如 Merge Request 或 Push 操作）时，GitLab 将自动触发 webhook
事件，调用本系统的接口。系统随后通过第三方大模型对代码进行审查，并将审查结果直接反馈到对应的 Merge Request 或 Commit 的
Note 中，便于团队查看和处理。

![流程图](doc/img/open/process.png)

## 部署

### 方案一：Docker 部署

**1. 准备环境文件**

- 克隆项目仓库：
```aiignore
git clone https://github.com/sunmh207/AI-Codereview-Gitlab.git
cd AI-Codereview-Gitlab
```

- 创建配置文件：
```aiignore
cp conf/.env.dist conf/.env
```

- 编辑 conf/.env 文件，配置以下关键参数：

```bash
#大模型供应商配置,支持 zhipuai , openai , deepseek 和 ollama
LLM_PROVIDER=deepseek

#DeepSeek
DEEPSEEK_API_KEY={YOUR_DEEPSEEK_API_KEY}

#支持review的文件类型(未配置的文件类型不会被审查)
SUPPORTED_EXTENSIONS=.java,.py,.php,.yml,.vue,.go,.c,.cpp,.h,.js,.css,.md,.sql

#钉钉消息推送: 0不发送钉钉消息,1发送钉钉消息
DINGTALK_ENABLED=0
DINGTALK_WEBHOOK_URL={YOUR_WDINGTALK_WEBHOOK_URL}

#企业微信消息推送
WECOM_ENABLED=0
WECOM_WEBHOOK_URL={YOUR_WECOM_WEBHOOK_URL}
# Push事件是否使用text消息类型（支持@人）：1=启用，0=使用markdown（默认）
PUSH_WECOM_USE_TEXT_MSG=0
# 日报专用webhook（可选）
# WECOM_WEBHOOK_URL_DAILY_REPORT={YOUR_DAILY_REPORT_WEBHOOK_URL}

#Gitlab配置
GITLAB_ACCESS_TOKEN={YOUR_GITLAB_ACCESS_TOKEN}
```

**2. 启动服务**

```bash
docker-compose up -d
docker-compose stop 
docker-compose rm
docker-compose ps
docker-compose restart
```

**3. 验证部署**

- 主服务验证：
  - 访问 http://your-server-ip:5001
  - 显示 "The code review server is running." 说明服务启动成功。
- Dashboard 验证：
  - 访问 http://your-server-ip:5002
  - 看到一个审查日志页面，说明 Dashboard 启动成功。

### 方案二：本地Python环境部署

**1. 获取源码**

```bash
git clone https://github.com/sunmh207/AI-Codereview-Gitlab.git
cd AI-Codereview-Gitlab
```

**2. 安装依赖**

使用 Python 环境（建议使用虚拟环境 venv）安装项目依赖(Python 版本：3.10+):

```bash
pip install -r requirements.txt
```

**3. 配置环境变量**

同 Docker 部署方案中的.env 文件配置。

**4. 启动服务**

- 启动API服务：

```bash
python api.py
```

- 启动Dashboard服务：

```bash
streamlit run ui.py --server.port=5002 --server.address=0.0.0.0
```

### 配置 GitLab Webhook

#### 1. 创建Access Token

方法一：在 GitLab 个人设置中，创建一个 Personal Access Token。

方法二：在 GitLab 项目设置中，创建Project Access Token

#### 2. 配置 Webhook

在 GitLab 项目设置中，配置 Webhook：

- URL：http://your-server-ip:5001/review/webhook
- Trigger Events：勾选 Push Events 和 Merge Request Events (不要勾选其它Event)
- Secret Token：上面配置的 Access Token(可选)

**备注**

1. Token使用优先级
  - 系统优先使用 .env 文件中的 GITLAB_ACCESS_TOKEN。
  - 如果 .env 文件中没有配置 GITLAB_ACCESS_TOKEN，则使用 Webhook 传递的Secret Token。
2. 网络访问要求
  - 请确保 GitLab 能够访问本系统。
  - 若内网环境受限，建议将系统部署在外网服务器上。

### 配置消息推送

#### 1.配置钉钉推送

- 在钉钉群中添加一个自定义机器人，获取 Webhook URL。
- 更新 .env 中的配置：
  ```
  #钉钉配置
  DINGTALK_ENABLED=1  #0不发送钉钉消息，1发送钉钉消息
  DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx #替换为你的Webhook URL
  ```

企业微信和飞书推送配置类似，具体参见 [常见问题](doc/faq.md)

## 高级配置

### 多级配置系统

支持为不同项目或命名空间配置独立的审查规则：

```bash
# 全局配置：conf/.env
LLM_PROVIDER=deepseek
REVIEW_STYLE=professional

# 命名空间级别：conf/{namespace}/.env
# 项目级别：conf/{namespace}/{project_name}/.env
# 优先级：项目级别 > 命名空间级别 > 全局配置
```

### Review 白名单

控制哪些项目允许进行代码审查：

```bash
# 开启白名单功能
REVIEW_WHITELIST_ENABLED=1

# 配置白名单（支持命名空间或完整项目路径）
# 示例1：按命名空间
REVIEW_WHITELIST=asset,frontend

# 示例2：按项目路径
REVIEW_WHITELIST=asset/asset-batch-center,frontend/web-app

# 示例3：混合配置
REVIEW_WHITELIST=asset,frontend/web-app,backend/api-gateway
```

### Commit Message 过滤

仅当 commit message 匹配指定规则时才触发 Review：

```bash
# 开启 commit message 检查
PUSH_COMMIT_MESSAGE_CHECK_ENABLED=1

# 配置匹配规则（支持正则表达式）
PUSH_COMMIT_MESSAGE_CHECK_PATTERN=review
# 或者：PUSH_COMMIT_MESSAGE_CHECK_PATTERN=\[review\]
# 或者：PUSH_COMMIT_MESSAGE_CHECK_PATTERN=(review|codereview)
```

### 企业微信 @人功能

Push 事件支持 text 消息格式，可 @commit 者：

```bash
# 启用 text 消息类型（支持@人）
PUSH_WECOM_USE_TEXT_MSG=1
```

### 日报专用推送配置

支持为日报功能配置独立的 webhook，与 push/merge 事件通知分开：

```bash
# 企业微信日报专用 webhook（可选）
WECOM_WEBHOOK_URL_DAILY_REPORT=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=daily-report-key

# 钉钉日报专用 webhook（可选）
DINGTALK_WEBHOOK_URL_DAILY_REPORT=https://oapi.dingtalk.com/robot/send?access_token=daily-report-token

# 飞书日报专用 webhook（可选）
FEISHU_WEBHOOK_URL_DAILY_REPORT=https://open.feishu.cn/open-apis/bot/v2/hook/daily-report-hook
```

**说明**：
- 日报专用配置仅使用全局默认配置（`conf/.env`），不查找项目或命名空间级别配置
- 如果未配置专用 webhook，则使用默认的 `{PLATFORM}_WEBHOOK_URL`
- 可以将日报推送到管理群，而 push/merge 事件推送到开发群

### 其他高级配置

```bash
# 仅对保护分支的合并请求进行 Review
MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED=1

# Review 风格：professional | sarcastic | gentle | humorous
REVIEW_STYLE=professional

# 每次 Review 的最大 Token 限制
REVIEW_MAX_TOKENS=10000
```

### 数据库配置

系统支持 SQLite 和 MySQL 两种数据库存储方式，默认使用 SQLite。

#### 使用 SQLite（默认）

```bash
# 数据库类型（默认：sqlite）
DB_TYPE=sqlite

# SQLite 数据库文件路径（默认：data/data.db）
DB_FILE=data/data.db
```

#### 使用 MySQL

```bash
# 数据库类型
DB_TYPE=mysql

# MySQL 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=ai_codereview
```

**MySQL 初始化**：

1. 创建数据库：
```sql
CREATE DATABASE ai_codereview CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. 导入表结构（可选，系统会自动创建）：
```bash
mysql -u root -p ai_codereview < doc/mysql_schema.sql
```

**说明**：
- SQLite：适合小型团队或个人使用，无需额外配置数据库服务
- MySQL：适合中大型团队，支持更高的并发性能和数据规模
- 切换数据库类型前，建议备份现有数据
- 详细使用说明请参见 [数据库使用指南](doc/database.md)

## 其它

**1.如何对整个代码库进行Review?**

可以通过命令行工具对整个代码库进行审查。当前功能仍在不断完善中，欢迎试用并反馈宝贵意见！具体操作如下：

```bash
python -m biz.cmd.review
```

运行后，请按照命令行中的提示进行操作即可。

**2.如何运行测试？**

项目的所有测试代码统一存放在 `test/` 目录下，组织结构与 `biz/` 目录对应。

```bash
# 运行所有测试
python -m unittest discover -s test -p "test_*.py" -v

# 运行特定模块的测试
python -m unittest test.biz.queue.test_whitelist -v
```

详细的测试说明请参见 [test/README.md](test/README.md)

**3.其它问题**

参见 [常见问题](doc/faq.md)

## 交流

若本项目对您有帮助，欢迎 Star ⭐️ 或 Fork。 有任何问题或建议，欢迎提交 Issue 或 PR。

也欢迎加微信/微信群，一起交流学习。

<p float="left">
  <img src="doc/img/open/wechat.jpg" width="400" />
  <img src="doc/img/open/wechat_group.jpg" width="400" /> 
</p>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=sunmh207/AI-Codereview-Gitlab&type=Timeline)](https://www.star-history.com/#sunmh207/AI-Codereview-Gitlab&Timeline)