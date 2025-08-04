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

### 同一个实例中是否支持给多个项目配置Review的提示词模板？     


同一个实例中，可以配置多个项目Review的提示词模板。具体操作如下：
#### 1. 创建项目提示词文件

首先，为特定项目创建自定义提示词文件，例如 `conf/myproject_prompt.yml`。

提示词文件格式可参考 [prompt_templates.yml](./conf/prompt_templates.yml)

#### 2. 配置环境变量

在 `.env` 文件中添加以下内容：

```shell
# 配置规则：项目名全大写 + _PROMPT = 提示词文件路径
PROJECT_NAME_PROMPT=conf/project_prompt.yml
```

例如，如果您的项目名为 `payment_service`，则应在 .env 文件中添加：

```shell
PAYMENT_SERVICE_PROMPT=conf/payment_service_prompt.yml
```

#### 3. 注意事项

- 如果未配置项目专属提示词，系统将使用默认提示词模板
- 项目提示词支持热加载，修改提示词文件后无需重启服务
- 环境变量配置后需要重启服务才能生效
- 项目名称中包含 `-` 时，请使用 `_` 替换
