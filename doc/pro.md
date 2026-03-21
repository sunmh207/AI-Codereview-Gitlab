[开源版](../README.md) |
[Pro版](pro.md)

# AI Codereview Pro版

AI Codereview Pro是基于大语言模型的自动化代码审查工具，旨在帮助开发团队提升代码质量、规范编码实践、减少人工审查负担。通过深度集成Git平台，提供从基础审查到项目级洞察的全面解决方案。

### 开源版 VS Pro版

开源版与 Pro 版均为基于大语言模型的 GitLab 自动代码审查工具，两者核心能力对比如下。

| 分类      | 功能特性   | 开源版                                             | Pro版                                                          |
|---------|--------|-------------------------------------------------|---------------------------------------------------------------|
| 产品定位    | 适用场景   | 提供基础的代码审查功能，适合二次开发与定制场景                         | 提供更强大的审查能力，支持项目分析与深度管理场景                                      |
|         | 技术栈    | Python + SQLite                                 | Vue + Java + MySQL                                            |
| 审查触发与集成 | 触发事件类型 | Push 与 Merge Request                            | 与开源版一致                                                        |
|         | 支持的代码平台 | GitLab / GitHub / Gitea                         | GitLab / GitHub / Gitee / Gitea                               |
|         | 触发方式   | Webhook 自动审查                                    | 与开源版一致                                                        |
|         | IM通知@提交者 | ❌ 不支持                                           | ✅ 支持设置代码评审分数阈值，低于阈值时钉钉/企微/飞书消息自动 @ 提交者                        |
| AI 能力   | 支持的模型  | DeepSeek、ZhipuAI、OpenAI、Anthropic、通义千问、Ollama 等 | DeepSeek、OpenAI、OpenRouter、ZhipuAI、Ollama、VLLM、阿里云百炼等         |
|         | 提示词自定义 | 全局统一提示词                                         | ✅ 支持按项目独立配置审查提示词                                              |
|         | 深度审查   | ❌ 不支持                                           | ✅ 深度审查：支持全项目及提交历史的综合分析                                        |
| 项目模板与复用 | 项目模板功能 | ❌ 不支持                                           | ✅ 支持创建项目模板，复用完整的评审配置（如文件扩展名过滤、审查提示词等），在多项目管理中大幅减少重复劳动，提升配置效率  |
|         | 自定义审查规则 | ❌ 不支持                                           | ✅ 支持在项目模板中配置自定义审查规则，可根据文件路径或类型自动匹配并注入特定的代码审查提示，实现精细化、自动化的审查策略 |
| 审查输出内容  | 结果展示   | 在 MR/Commit 中生成评审建议注释                           | 支持 MR/Commit 注释 + 系统内统一查看界面                                   |
|         | 审查风格   | 预设风格：专业、讽刺、绅士、幽默                                | 支持按项目自定义提示词，灵活适配项目风格                                          |
|         | 报告总结   | 基础摘要                                            | 增强型报告与可视化图表展示                                                 |
| 消息通知    | 推送渠道   | 钉钉/企业微信/飞书                                      | 与开源版一致                                                        |
| 数据与报表   | Dashboard | 单页面 Dashboard                                   | ✅ 更多统计图（类别更丰富）                                                |
|         | 成员分析   | ❌ 不支持                                           | ✅ 支持开发者提交行为分析                                                 |
|         | 系统配置   | 通过修改 .env 文件配置                                  | 可视化配置界面，支持 IM 机器人、大模型、项目等灵活设置与搭配                              |
|         | 日志管理   | 控制台输出                                           | 控制台输出 + 日志查询界面，支持历史记录检索与筛选                                    |
| 权限管理    | 用户与角色  | ❌ 不支持                                           | ✅ 支持用户管理与角色管理，可配置菜单访问权限                                 |
| 项目监控    | 报告生成   | 自动生成日报                                          | 支持自定义日报/周报/月报...                                              |
|         | 主动监控   | ❌ 不支持                                           | ✅ 项目哨兵：支持自定义监控逻辑与预警频率                                         |
| 部署与体验   | 部署方式   | Python 运行 / Docker 部署                           | Docker 部署                                                     |
|         | 体验方式   | ❌ 无                                             | ✅ 提供线上体验站：https://demo.mzfuture.com                           |

### Pro版 部分截图

**多种统计图**
![Dashboard](img/pro/dashboard.png)

**成员提交分析**
![Dashboard](img/pro/member-analysis.png)

**Deep Review**
![Dashboard](img/pro/deepreview.png)

**项目哨兵**
![Dashboard](img/pro/project-analysis-plan.png)

## 体验站

地址: [https://demo.mzfuture.com](https://demo.mzfuture.com)

## 部署

### 1. 准备环境

创建docker-compose.yml文件

```yaml
services:
  mysql:
    image: mysql:8.0.44
    container_name: codereview-mysql
    environment:
      MYSQL_ROOT_PASSWORD: u9QdPyXM
      MYSQL_DATABASE: codereview
      TZ: Asia/Shanghai
    command:
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_general_ci
      --explicit_defaults_for_timestamp=1
      --lower_case_table_names=1
    volumes:
      - ./data/mysql:/var/lib/mysql
    healthcheck:
      test: [ "CMD", "mysqladmin", "ping", "-h", "localhost", "-pu9QdPyXM" ]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 30s
    restart: unless-stopped

  app:
    image: registry.cn-hangzhou.aliyuncs.com/stanley-public/ai-codereview-pro:1.5.0
    container_name: codereview-app
    ports:
      - "81:80"
    environment:
      APP_USERNAME: admin
      APP_PASSWORD: admin
      DB_HOST: mysql
      DB_PORT: 3306
      DB_NAME: codereview
      DB_USERNAME: root
      DB_PASSWORD: u9QdPyXM
      TZ: Asia/Shanghai
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped
```

如果存在2级路由,见解决方案 [二级路由场景部署方案](pro-proxy.md)

### 2. 启动服务

```bash
docker-compose up -d
```

### 3. 访问管理后台

打开浏览器，访问 http://localhost:81 ，使用用户名 `admin` 和密码 `admin` 登录。

### 4. 系统配置

按照实际情况，在系统内增加项目、大模型、通知机器人等信息。

## 配置代码库 Webhook (以Gitlab为例)

### 1. 创建Access Token

方法一：在 GitLab 个人设置中，创建一个 Personal Access Token。

方法二：在 GitLab 项目设置中，创建Project Access Token

### 2. 配置 Webhook

在 GitLab 项目设置中，配置 Webhook：

- URL：http://your-server-ip:81/review/webhook
- Trigger Events：勾选 Push Events 和 Merge Request Events (不要勾选其它Event)
- Secret Token：上面配置的 Access Token(可选)

### 3. 测试 Webhook

在Gitlab Webhook配置页面, 选择"Test" -> "Push Events"

### 到管理后台查看结果
