# 应用专属配置指南

## 功能概述

系统支持按应用名（GitLab/GitHub URL slug）独立配置 `.env` 和 `prompt_templates.yml` 文件。这意味着不同的代码仓库可以使用不同的配置，实现更灵活的多项目管理。

## 配置优先级

系统采用以下配置加载优先级：

1. **应用专属配置** > **默认配置**
   - `.env`: `conf/{app_name}/.env` > `conf/.env`
   - `prompt_templates.yml`: `conf/{app_name}/prompt_templates.yml` > `conf/prompt_templates.yml`

2. 如果应用专属配置文件不存在，则自动降级使用默认配置

## 应用名称（URL Slug）生成规则

应用名称由 GitLab/GitHub URL 自动生成，生成规则如下：

- 移除 URL 的协议前缀（http://、https://）
- 将非字母数字字符替换为下划线
- 移除末尾的下划线

**示例：**
```
http://gitlab.example.com/  => gitlab_example_com
https://github.com/user/repo.git  => github_com_user_repo_git
http://git.test.cn:8080/project  => git_test_cn_8080_project
```

## 配置步骤

### 1. 创建应用专属配置目录

在 `conf/` 目录下创建以应用名命名的子目录：

```bash
mkdir conf/{app_name}
```

**示例：**
```bash
# 为 gitlab.example.com 创建配置目录
mkdir conf/gitlab_example_com

# 为 github.com 创建配置目录
mkdir conf/github_com
```

### 2. 创建应用专属配置文件

#### 方式一：复制默认配置后修改

```bash
# 复制 .env 配置
cp conf/.env conf/{app_name}/.env

# 复制 prompt_templates.yml 配置
cp conf/prompt_templates.yml conf/{app_name}/prompt_templates.yml
```

#### 方式二：只创建需要覆盖的配置

如果只需要覆盖部分配置，可以只创建对应的配置文件。例如，只想为某个应用定制 Prompt 模板，则只需创建 `conf/{app_name}/prompt_templates.yml`。

### 3. 修改配置内容

根据具体需求修改配置文件。常见的定制场景包括：

#### .env 配置定制示例

```bash
# conf/gitlab_example_com/.env

# 使用不同的 LLM 供应商
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-specific-key

# 使用不同的 Review 风格
REVIEW_STYLE=humorous

# 使用不同的企微机器人
WECOM_ENABLED=1
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=app-specific-key

# 支持不同的文件类型
SUPPORTED_EXTENSIONS=.java,.py,.js,.ts
```

#### prompt_templates.yml 定制示例

```yaml
# conf/gitlab_example_com/prompt_templates.yml

code_review_prompt:
  system_prompt: |-
    你是一位专注于Java后端开发的资深工程师，请重点关注以下方面：
    1. Spring Boot 最佳实践
    2. MyBatis SQL 优化
    3. 并发安全问题
    4. 性能优化建议
    
    # ... 其他自定义内容
    
  user_prompt: |-
    请审查以下 Java 代码变更：
    
    代码变更内容：
    {diffs_text}
    
    提交历史：
    {commits_text}
```

## 使用场景示例

### 场景一：不同项目使用不同的 LLM

```
项目 A (gitlab.company.com)
├── conf/gitlab_company_com/.env
│   └── LLM_PROVIDER=deepseek

项目 B (github.com)
├── conf/github_com/.env
│   └── LLM_PROVIDER=zhipuai
```

### 场景二：不同项目使用不同的 Review 风格

```
严肃项目 (git.product.com)
├── conf/git_product_com/.env
│   └── REVIEW_STYLE=professional

内部项目 (git.internal.com)
├── conf/git_internal_com/.env
│   └── REVIEW_STYLE=humorous
```

### 场景三：不同项目发送到不同的消息群

```
团队 A (gitlab.team-a.com)
├── conf/gitlab_team_a_com/.env
│   └── WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/...?key=team-a-key

团队 B (gitlab.team-b.com)
├── conf/gitlab_team_b_com/.env
│   └── WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/...?key=team-b-key
```

### 场景四：不同项目使用不同的 Prompt 模板

```
前端项目 (git.frontend.com)
├── conf/git_frontend_com/prompt_templates.yml
│   └── 专注于 Vue/React 代码审查

后端项目 (git.backend.com)
├── conf/git_backend_com/prompt_templates.yml
│   └── 专注于 Java/Python 代码审查
```

## 配置文件结构示例

```
conf/
├── .env                          # 默认环境变量配置
├── prompt_templates.yml          # 默认 Prompt 模板
├── example_app/                  # 示例应用配置
│   ├── .env                      # 示例应用的环境变量
│   └── prompt_templates.yml      # 示例应用的 Prompt 模板
├── gitlab_example_com/           # gitlab.example.com 的配置
│   ├── .env
│   └── prompt_templates.yml
├── github_com/                   # github.com 的配置
│   └── .env                      # 只覆盖环境变量，使用默认 Prompt
└── git_internal_company_com/     # git.internal.company.com 的配置
    └── prompt_templates.yml      # 只覆盖 Prompt，使用默认环境变量
```

## 技术实现原理

1. **Webhook 触发时**：系统从 Webhook 数据中提取 GitLab/GitHub URL
2. **生成 URL Slug**：使用 `slugify_url()` 函数将 URL 转换为应用名
3. **加载配置**：`ConfigLoader` 根据应用名加载对应的配置文件
4. **配置覆盖**：应用专属配置会覆盖已加载的默认配置

## 注意事项

1. **配置文件编码**：所有配置文件必须使用 UTF-8 编码
2. **目录命名**：应用配置目录名必须与 URL Slug 完全一致
3. **配置热更新**：
   - 使用 Docker 部署时，修改配置后需要重启容器
   - 本地运行时，修改配置后需要重启服务
4. **日志查看**：可以通过日志确认使用了哪个配置文件：
   ```
   [INFO] 使用应用专属配置: conf/gitlab_example_com/.env
   [INFO] 使用默认配置: conf/.env
   ```

## 常见问题

### Q1: 如何确认应用名是什么？

查看系统日志，在 Webhook 触发时会输出类似以下内容：
```
[INFO] Received event: merge_request
[INFO] ConfigLoader设置应用名称: gitlab_example_com
```

### Q2: 配置不生效怎么办？

1. 检查目录名是否与 URL Slug 一致
2. 检查配置文件名是否正确（.env 或 prompt_templates.yml）
3. 查看日志确认加载了哪个配置文件
4. 确认已重启服务

### Q3: 可以只覆盖部分配置吗？

不可以。如果创建了应用专属的 `.env` 文件，该文件会完全替代默认的 `.env`，因此需要包含所有必要的配置项。建议从默认配置复制后再修改。

### Q4: Docker 部署时如何管理多个应用的配置？

在 `docker-compose.yml` 中映射整个 `conf/` 目录：
```yaml
volumes:
  - ./conf:/app/conf
```

然后在宿主机的 `conf/` 目录下创建各应用的配置子目录。

## 示例参考

系统提供了示例配置供参考：
- `conf/example_app/.env` - 示例环境变量配置
- `conf/example_app/prompt_templates.yml` - 示例 Prompt 模板配置

可以复制这些文件作为起点进行定制。
