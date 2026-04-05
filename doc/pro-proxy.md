### 二级路由场景部署方案

- 特殊场景 创建docker-compose.yml文件（适用存在2级路由，例如你的gitlab主站域名为x.x.com/gitlab）：
- 原理：通过nginx劫持ai-codereview-pro应用的访问，强行加入/gitlab

```
services:
  mysql:
    image: mysql:8.0
    container_name: codereview-mysql
    privileged: true
    environment:
      MYSQL_ROOT_PASSWORD: u9QdPyXM
      MYSQL_DATABASE: codereview
      TZ: Asia/Shanghai
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_general_ci
    volumes:
      - ./data/mysql:/var/lib/mysql
    restart: unless-stopped
    networks:
      - internal
  app:
    image: registry.cn-hangzhou.aliyuncs.com/stanley-public/ai-codereview-pro:1.5.4
    container_name: codereview-app
    privileged: true
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
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - mysql
    restart: unless-stopped
    networks:
      - internal
  proxy:
    image: nginx:1.29.3-alpine3.22-slim
    container_name: codereview-proxy
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    ports:
      - "443:443"
    restart: unless-stopped
    networks:
      internal:
        aliases:
          - x.x.com
networks:
  internal:
    driver: bridge

```

特殊场景 中的nginx.conf

```
events {}
http {
    upstream real_gitlab {
        # 把 <REAL_IP> 换成 x.x.com 的真实地址
        server 192.168.1.2:443;
    }

    server {
        listen 443 ssl;
        server_name x.x.com;

        ssl_certificate     /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;

        location / {
            # 统一加 /gitlab 前缀
            rewrite ^(.*)$ /gitlab$1 break;

            proxy_pass https://real_gitlab;
            proxy_ssl_verify        off;   # 自签/内网必需
            proxy_ssl_server_name   on;
            proxy_set_header Host   x.x.com;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_connect_timeout   10s;
        }
    }
}
```