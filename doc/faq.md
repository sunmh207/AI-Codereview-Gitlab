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

#### 4.docker 容器部署时，连接Ollama失败

**可能原因**

配置127.0.0.1:11434连接Ollama。由于docker容器的网络模式为bridge，容器内的127.0.0.1并不是宿主机的127.0.0.1，所以连接失败。

**解决方案**

在.env文件中修改OLLAMA_API_BASE_URL为宿主机的IP地址或外网IP地址。同时要配置Ollama服务绑定到宿主机的IP地址（或0.0.0.0）。

```
OLLAMA_API_BASE_URL=http://127.0.0.1:11434  # 错误
OLLAMA_API_BASE_URL=http://{宿主机/外网IP地址}:11434  # 正确
```