# 应用专属配置快速入门

本指南帮助你快速上手应用专属配置功能。

## 5分钟快速配置

### 步骤1：确定应用名称

应用名称由 GitLab/GitHub URL 自动生成。

**示例：**
- 如果你的 GitLab 地址是 `http://gitlab.example.com`
- 那么应用名称就是 `gitlab_example_com`

**生成规则：**
```
移除 http:// 或 https://
将所有非字母数字字符替换为下划线 _
移除末尾的下划线
```

**更多示例：**
```
http://git.company.cn/        => git_company_cn
https://github.com/           => github_com
http://code.test.com:8080/    => code_test_com_8080
```

### 步骤2：创建配置目录

```bash
# 进入项目目录
cd AI-Codereview-Gitlab

# 创建应用配置目录（替换 {app_name} 为你的应用名）
mkdir -p conf/{app_name}

# 示例：为 gitlab.example.com 创建配置
mkdir -p conf/gitlab_example_com
```

### 步骤3：复制配置文件

```bash
# 复制 .env 配置文件
cp conf/.env conf/{app_name}/.env

# 复制 prompt 模板文件（可选，如果不需要定制 prompt 可以跳过）
cp conf/prompt_templates.yml conf/{app_name}/prompt_templates.yml

# 示例
cp conf/.env conf/gitlab_example_com/.env
cp conf/prompt_templates.yml conf/gitlab_example_com/prompt_templates.yml
```

### 步骤4：修改配置

编辑 `conf/{app_name}/.env` 文件，修改你需要定制的配置项。

**常见定制场景：**

#### 场景A：使用不同的 LLM

```bash
# 编辑 conf/gitlab_example_com/.env

# 修改 LLM 供应商为 DeepSeek
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-deepseek-key
DEEPSEEK_API_MODEL=deepseek-chat
```

#### 场景B：使用不同的 Review 风格

```bash
# 编辑 conf/gitlab_example_com/.env

# 修改 Review 风格为幽默型
REVIEW_STYLE=humorous
```

#### 场景C：发送到不同的消息群

```bash
# 编辑 conf/gitlab_example_com/.env

# 修改企微 Webhook
WECOM_ENABLED=1
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=team-specific-key
```

#### 场景D：支持不同的文件类型

```bash
# 编辑 conf/gitlab_example_com/.env

# 只审查 Java 和 Python 文件
SUPPORTED_EXTENSIONS=.java,.py
```

### 步骤5：重启服务

**Docker 部署：**
```bash
docker-compose restart
```

**本地部署：**
```bash
# 停止当前运行的服务（Ctrl+C）
# 然后重新启动
python api.py
```

### 步骤6：验证配置

触发一次 GitLab Webhook（提交代码或创建 MR），然后查看日志：

**查看 Docker 日志：**
```bash
docker-compose logs -f app
```

**预期日志输出：**
```
[INFO] ConfigLoader设置应用名称: gitlab_example_com
[INFO] 使用应用专属配置: conf/gitlab_example_com/.env
[INFO] 成功加载Prompt模板 code_review_prompt from conf/gitlab_example_com/prompt_templates.yml
```

如果看到 "使用应用专属配置"，说明配置成功！

## 常见配置示例

### 示例1：为不同团队配置不同的消息推送

```
conf/
├── team_a_gitlab_com/
│   └── .env                 # WECOM_WEBHOOK_URL=团队A的webhook
├── team_b_gitlab_com/
│   └── .env                 # WECOM_WEBHOOK_URL=团队B的webhook
└── team_c_gitlab_com/
    └── .env                 # DINGTALK_WEBHOOK_URL=团队C的钉钉webhook
```

### 示例2：不同项目使用不同的 LLM

```
conf/
├── prod_gitlab_com/
│   └── .env                 # LLM_PROVIDER=deepseek (生产项目用更强大的模型)
└── test_gitlab_com/
    └── .env                 # LLM_PROVIDER=zhipuai (测试项目用性价比高的模型)
```

### 示例3：前后端项目使用不同的 Prompt

```
conf/
├── frontend_repo/
│   └── prompt_templates.yml # 专注于 Vue/React 代码审查
└── backend_repo/
    └── prompt_templates.yml # 专注于 Java/Python 代码审查
```

## 注意事项

### ✅ 必须做的事情

1. **目录名必须准确**：应用配置目录名必须与 URL slug 完全一致
2. **编码为 UTF-8**：所有配置文件必须使用 UTF-8 编码
3. **包含所有配置**：`.env` 文件需要包含所有必要的配置项
4. **重启服务**：修改配置后必须重启服务才能生效

### ❌ 不要做的事情

1. **不要只修改部分配置项**：`.env` 文件会完全替换默认配置，必须包含所有配置项
2. **不要使用错误的目录名**：目录名必须是 URL slug，而不是项目名
3. **不要忘记重启**：修改配置后不重启服务不会生效

## 快速诊断

### 问题：配置没有生效

**解决步骤：**

1. 检查目录名是否正确
   ```bash
   # 查看日志中的应用名称
   docker-compose logs app | grep "ConfigLoader设置应用名称"
   ```

2. 检查配置文件是否存在
   ```bash
   ls -la conf/{app_name}/
   ```

3. 检查是否重启了服务
   ```bash
   docker-compose restart
   ```

4. 查看日志确认加载的配置文件
   ```bash
   docker-compose logs app | grep "使用.*配置"
   ```

### 问题：不知道应用名称是什么

**解决方法：**

查看 Webhook 触发时的日志：
```bash
docker-compose logs app | grep "Received event"
```

在日志中会显示应用名称，例如：
```
[INFO] ConfigLoader设置应用名称: gitlab_example_com
```

### 问题：配置文件格式错误

**解决方法：**

1. 检查文件编码（必须是 UTF-8）
2. 检查 YAML 格式是否正确（注意缩进）
3. 参考示例配置文件：`conf/example_app/`

## 进阶技巧

### 技巧1：只覆盖 Prompt 模板

如果只想定制 Prompt 模板，可以只创建 `prompt_templates.yml`：

```bash
mkdir -p conf/gitlab_example_com
cp conf/prompt_templates.yml conf/gitlab_example_com/prompt_templates.yml
# 编辑 prompt_templates.yml
# 不需要创建 .env 文件，会自动使用默认的 .env
```

### 技巧2：批量创建配置

```bash
# 为多个项目创建配置目录
for app in gitlab_team_a_com gitlab_team_b_com github_com; do
    mkdir -p conf/$app
    cp conf/.env conf/$app/.env
    echo "Created config for $app"
done
```

### 技巧3：使用环境变量模板

创建一个配置模板文件，方便快速生成新配置：

```bash
# 创建模板
cat > conf/template.env << 'EOF'
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxx
REVIEW_STYLE=professional
WECOM_ENABLED=1
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
EOF

# 使用模板创建新配置
cp conf/template.env conf/new_app/.env
```

## 获取帮助

如有问题，请参考：
- 详细文档：[doc/app_config_guide.md](./app_config_guide.md)
- 实现说明：[doc/app_config_implementation.md](./app_config_implementation.md)
- 示例配置：`conf/example_app/`
- 提交 Issue：[GitHub Issues](https://github.com/sunmh207/AI-Codereview-Gitlab/issues)
