## 常见问题

### Docker 容器部署时，更新 .env 文件后不生效

**可能原因**

Docker 的文件映射机制是将宿主机的文件复制到容器内，因此宿主机文件的更新不会自动同步到容器内。

**解决方案**

- 删除现有容器：

```
docker rm -f <container_name>
```

重新创建并启动容器：

```
docker-compose up -d
```

或参考说明文档启动容器。

### GitLab 配置 Webhooks 时提示 "Invalid url given"

**可能原因**

GitLab 默认禁止 Webhooks 访问本地网络地址。

**解决方案**

- 进入 GitLab 管理区域：Admin Area → Settings → Network。
- 在 Outbound requests 部分，勾选 Allow requests to the local network from webhooks and integrations。
- 保存。

### 如何让不同项目的消息发送到不同的群？

**解决方案**

在项目的 .env 文件中，配置不同项目的群机器人的 Webhook 地址。
以 DingTalk 为例，配置如下：

```
DINGTALK_ENABLED=1
#项目A的群机器人的Webhook地址
DINGTALK_WEBHOOK_URL_PROJECT_A=https://oapi.dingtalk.com/robot/send?access_token={access_token_of_project_a}
#项目B的群机器人的Webhook地址
DINGTALK_WEBHOOK_URL_PROJECT_B=https://oapi.dingtalk.com/robot/send?access_token={access_token_of_project_b}
#保留默认WEBHOOK_URL，发送日报或者其它项目将使用此URL
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token={access_token}
```

飞书和企业微信的配置方式类似。

### 如何让不同的Gitlab服务器的消息发送到不同的群？

在项目的 .env 文件中，配置不同Gitlab服务器的群机器人的 Webhook 地址。
以 DingTalk 为例，配置如下：

```
DINGTALK_ENABLED=1
# Gitlab服务器A(http://192.168.30.164)的群机器人的Webhook地址
DINGTALK_WEBHOOK_192_168_30_164=https://oapi.dingtalk.com/robot/send?access_token={access_token_of_gitlab_server_a}
# Gitlab服务器B(http://example.gitlab.com)的群机器人的Webhook地址
DINGTALK_WEBHOOK_example_gitlab_com=https://oapi.dingtalk.com/robot/send?access_token={access_token_of_gitlab_server_b}
```

飞书和企业微信的配置方式类似。

**优先级：** 优先根据仓库名称匹配webhook地址，其次根据Gitlab服务器地址匹配webhook地址，如果都没有匹配到，则最后使用默认服务器地址

### docker 容器部署时，连接Ollama失败

**可能原因**

配置127.0.0.1:11434连接Ollama。由于docker容器的网络模式为bridge，容器内的127.0.0.1并不是宿主机的127.0.0.1，所以连接失败。

**解决方案**

在.env文件中修改OLLAMA_API_BASE_URL为宿主机的IP地址或外网IP地址。同时要配置Ollama服务绑定到宿主机的IP地址（或0.0.0.0）。

```
OLLAMA_API_BASE_URL=http://127.0.0.1:11434  # 错误
OLLAMA_API_BASE_URL=http://{宿主机/外网IP地址}:11434  # 正确
```

### 如何使用Redis Queue队列？

**操作步骤**

1.开发调试模式下，启动容器：

```
docker compose -f docker-compose.rq.yml up -d
```

2.生产模式下，启动容器：

```
docker compose -f docker-compose.prod.yml up -d
```

**特别说明：**

在 .env 文件中配置 WORKER_QUEUE，其值为 GitLab 域名，并将域名中的点（.）替换为下划线（_）。如果域名为 gitlab.test.cn，则配置为：

```
WORKER_QUEUE=gitlab_test_cn
```

### 如何配置企业微信和飞书消息推送？

**1.配置企业微信推送**

- 在企业微信群中添加一个自定义机器人，获取 Webhook URL。

- 更新 .env 中的配置：
  ```
  #企业微信配置
  WECOM_ENABLED=1  #0不发送企业微信消息，1发送企业微信消息
  WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx  #替换为你的Webhook URL
  ```

**2.配置飞书推送**

- 在飞书群中添加一个自定义机器人，获取 Webhook URL。
- 更新 .env 中的配置：
  ```
  #飞书配置
  FEISHU_ENABLED=1
  FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx #替换为你的Webhook URL
  ```

### 是否支持对 GitHub 代码库的 Review？

是的，支持。 需完成以下配置：

**1.配置Github Webhook**

- 进入你的 GitHub 仓库 → Settings → Webhooks → Add webhook。
    - Payload URL: http://your-server-ip:5001/review/webhook（替换为你的服务器地址）
    - Content type选择application/json
    - 在 Which events would you like to trigger this webhook? 中选择 Just the push event（或按需勾选其他事件）
    - 点击 Add webhook 完成配置。

**2.生成 GitHub Personal Access Token**

- 进入 GitHub 个人设置 → Developer settings → Personal access tokens → Generate new token。
- 选择 Fine-grained tokens 或 tokens (classic) 都可以
- 点击 Create new token
- Repository access根据需要选择
- Permissions需要选择Commit statuses、Contents、Discussions、Issues、Metadata和Pull requests
- 点击 Generate token 完成配置。

**3.配置.env文件**

- 在.env文件中，配置GITHUB_ACCESS_TOKEN：
  ```
  GITHUB_ACCESS_TOKEN=your-access-token  #替换为你的Access Token
  ```

### 如何使用 Claude Code 进行代码审查？

Claude Code 是 Anthropic 提供的专门针对代码理解和生成优化的 AI 模型。要使用 Claude Code 进行代码审查，需要完成以下配置：

**1. 安装 Claude Code CLI**

Claude Code 需要通过命令行工具调用。首先确保你的系统已安装 Node.js 18 或更高版本，然后全局安装 Claude Code CLI：

```bash
npm install -g @anthropic-ai/claude-code
```

**2. 获取 Anthropic API 密钥**

- 访问 [Anthropic Console](https://console.anthropic.com/settings/keys)
- 登录或注册账号
- 创建新的 API 密钥
- 复制 API 密钥（以 sk-ant- 开头）

**3. 配置 .env 文件**

在 .env 文件中添加以下配置：

```bash
# 设置 LLM 提供商为 claudecode
LLM_PROVIDER=claudecode

# Claude Code API 密钥
CLAUDE_CODE_API_KEY=sk-ant-your-api-key-here

# Claude API Base URL（可选，默认为 https://api.anthropic.com）
# 如果使用自定义 API 端点，可以修改此配置
CLAUDE_CODE_API_BASE_URL=https://api.anthropic.com

# 选择模型（可选，默认为 sonnet）
# 可选值: sonnet(推荐), opus(最高质量), haiku(最快速度)
CLAUDE_CODE_API_MODEL=sonnet
```

**4. 配置额外环境变量（可选）**

如果你需要通过代理访问 Claude API 或使用自定义 CA 证书，可以在 .env 文件中使用 `CLAUDE_CODE_ENV_` 前缀配置:

```bash
# Claude Code 环境变量配置
# HTTP 代理配置
CLAUDE_CODE_ENV_http_proxy=http://127.0.0.1:8899
CLAUDE_CODE_ENV_https_proxy=http://127.0.0.1:8899
CLAUDE_CODE_ENV_HTTP_PROXY=http://127.0.0.1:8899
CLAUDE_CODE_ENV_HTTPS_PROXY=http://127.0.0.1:8899

# 自定义 CA 证书（用于企业内网环境）
CLAUDE_CODE_ENV_NODE_EXTRA_CA_CERTS=/path/to/rootCA.cer
```

**配置说明**:
- **代理配置**: 使用 `CLAUDE_CODE_ENV_http_proxy` 和 `CLAUDE_CODE_ENV_https_proxy` 配置代理地址,建议同时配置小写和大写形式以确保兼容性
- **CA 证书**: 使用 `CLAUDE_CODE_ENV_NODE_EXTRA_CA_CERTS` 指定自定义根证书路径,常用于企业内网环境中需要自签名证书的场景
- **配置隔离**: 使用 `CLAUDE_CODE_ENV_` 前缀保持配置的统一性和隔离性,这些配置只会影响 Claude Code CLI 的执行,不会影响系统其他部分

**5. 重启服务**

```bash
docker-compose restart
# 或
python api.py
```

### Claude Code 配置常见错误排查

**错误：Claude Code CLI 未安装**

- 错误信息：`Claude Code CLI 未安装,请运行: npm install -g @anthropic-ai/claude-code`
- 解决方案：
  - 确保已安装 Node.js 18 或更高版本：`node --version`
  - 运行安装命令：`npm install -g @anthropic-ai/claude-code`
  - 验证安装：`claude --version`

**错误：Claude Code 认证失败**

- 错误信息：`Claude Code 认证失败,请检查 ANTHROPIC_API_KEY 是否正确配置`
- 解决方案：
  - 检查 .env 文件中的 CLAUDE_CODE_API_KEY 是否正确配置
  - 确认 API 密钥以 sk-ant- 开头
  - 验证 API 密钥是否过期或被撤销
  - 在 [Anthropic Console](https://console.anthropic.com/settings/keys) 重新生成密钥

**错误：Claude Code 模型配置错误**

- 错误信息：`Claude Code 模型配置错误,请使用 sonnet/opus/haiku`
- 解决方案：
  - 检查 CLAUDE_CODE_API_MODEL 配置值
  - 确保使用正确的模型名称：sonnet、opus 或 haiku
  - 如果未配置，系统将使用默认模型 sonnet

**错误：Claude Code 执行超时**

- 错误信息：`Claude Code 执行超时,请稍后重试或检查代码大小`
- 解决方案：
  - 检查代码文件是否过大（超过 10000 tokens）
  - 尝试减小 REVIEW_MAX_TOKENS 配置值
  - 检查网络连接是否正常
  - 稍后重试

**Docker 部署注意事项**

如果使用 Docker 部署，需要确保容器内也安装了 Node.js 和 Claude Code CLI。建议在 Dockerfile 中添加：

```dockerfile
# 安装 Node.js
RUN apt-get update && apt-get install -y nodejs npm

# 安装 Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code
```

