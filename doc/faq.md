### 常见问题

#### 1.Docker 容器部署时，更新 .env 文件后不生效

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

#### 2. GitLab 配置 Webhooks 时提示 "Invalid url given"

**可能原因**

GitLab 默认禁止 Webhooks 访问本地网络地址。

**解决方案**

- 进入 GitLab 管理区域：Admin Area → Settings → Network。
- 在 Outbound requests 部分，勾选 Allow requests to the local network from webhooks and integrations。
- 保存。

#### 3.如何让不同项目的消息发送到不同的群？

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

#### 4.如何让不同的Gitlab服务器的消息发送到不同的群？

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

#### 5.docker 容器部署时，连接Ollama失败

**可能原因**

配置127.0.0.1:11434连接Ollama。由于docker容器的网络模式为bridge，容器内的127.0.0.1并不是宿主机的127.0.0.1，所以连接失败。
对于Docker Desktop，请使用此地址连接Ollama: http://host.docker.internal:11434。

**解决方案**

在.env文件中修改OLLAMA_API_BASE_URL为宿主机的IP地址或外网IP地址。同时要配置Ollama服务绑定到宿主机的IP地址（或0.0.0.0）。

```
OLLAMA_API_BASE_URL=http://127.0.0.1:11434  # 错误
OLLAMA_API_BASE_URL=http://{宿主机/外网IP地址}:11434  # 正确
```

#### 6.如何使用Redis Queue队列？

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

#### 7. 如何配置企业微信和飞书消息推送？

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

#### 8. 翻译

更改翻译后无法正确应用，我该怎么办？
该应用程序使用 python 原生 gettext 实现来加载各种语言的翻译。如果您更改了翻译文件，但是应用程序没有正确应用新的翻译，您可以尝试以下步骤：
1. 更新翻译: `bash translations_update.sh`
2. 通过向具有空 msgstr 的新行添加值来手动调整 `locales/<locale>/LC_Messages/messages.po` 中缺失的翻译
3. 编译翻译：`bash translations_compile.sh`
4. 重新启动您的应用程序
