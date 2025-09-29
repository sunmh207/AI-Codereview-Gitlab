# 前后端分离架构部署和测试指南

## 架构概述

这个项目已经从原来的 Streamlit 单体应用改造为前后端分离架构：

- **前端**: Vue.js + TypeScript + Element Plus + ECharts
- **后端**: Flask API + JWT认证 + CORS支持
- **代理**: Nginx 反向代理，统一服务静态文件和API
- **部署**: Docker 多阶段构建，支持生产环境部署

## 快速开始

### 1. 开发环境设置

#### 启动后端 API

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 配置环境变量
cp conf/.env.dist conf/.env
# 编辑 conf/.env 文件，配置必要的环境变量

# 启动 Flask API (端口 5001)
python api.py
```

#### 启动前端开发服务器

```bash
# 进入前端目录
cd frontend

# 安装 Node.js 依赖
npm install

# 启动开发服务器 (端口 3000)
npm run dev
```

### 2. 生产环境部署

#### 使用 Docker Compose

```bash
# 构建并启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app
```

访问应用：
- 前端界面: http://localhost
- API文档: http://localhost/api/
- 原有webhook: http://localhost/review/webhook

#### 手动构建和部署

```bash
# 构建前端
cd frontend
npm install
npm run build

# 构建 Docker 镜像
cd ..
docker build -t ai-codereview:latest .

# 运行容器
docker run -d \
  --name ai-codereview \
  -p 80:80 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/log:/app/log \
  --env-file ./conf/.env \
  ai-codereview:latest
```

## 功能测试

### 1. 前端界面测试

#### 登录功能测试

1. 访问 http://localhost (或开发环境的 http://localhost:3000)
2. 应该自动跳转到登录页面
3. 使用默认凭据登录：
   - 用户名: `admin`
   - 密码: `admin`
4. 登录成功后应跳转到 Dashboard 页面

#### Dashboard 功能测试

1. **数据筛选**:
   - 修改开始和结束日期
   - 选择不同的开发者和项目
   - 切换"合并请求"和"代码推送"标签页

2. **图表显示**:
   - 验证项目提交统计图表
   - 验证项目平均得分图表
   - 验证开发者提交统计图表
   - 验证开发者平均得分图表
   - 验证代码变更行数图表（如果有数据）

3. **数据表格**:
   - 验证数据表格显示
   - 测试排序功能
   - 测试"查看详情"链接（MR页面）

### 2. API 接口测试

#### 认证接口测试

```bash
# 登录测试
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# 使用返回的 token 验证认证
curl -X GET http://localhost/api/auth/verify \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### 数据接口测试

```bash
# 获取元数据
curl -X GET http://localhost/api/metadata \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# 获取 MR 审查数据
curl -X GET "http://localhost/api/reviews/mr?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# 获取项目统计
curl -X GET "http://localhost/api/statistics/projects?type=mr" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 3. Webhook 功能测试

#### GitLab Webhook 测试

```bash
# 模拟 GitLab MR webhook
curl -X POST http://localhost/review/webhook \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: YOUR_GITLAB_TOKEN" \
  -d @test_gitlab_webhook.json
```

#### GitHub Webhook 测试

```bash
# 模拟 GitHub PR webhook
curl -X POST http://localhost/review/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -H "X-GitHub-Token: YOUR_GITHUB_TOKEN" \
  -d @test_github_webhook.json
```

## 故障排除

### 1. 前端相关问题

#### 开发服务器启动失败
```bash
# 清理 node_modules 并重新安装
cd frontend
rm -rf node_modules package-lock.json
npm install
```

#### API 请求失败
- 检查 Vite 代理配置（`vite.config.ts`）
- 确保后端 API 在端口 5001 运行
- 检查 CORS 配置

### 2. 后端相关问题

#### Flask API 启动失败
```bash
# 检查 Python 依赖
pip install -r requirements.txt

# 检查环境变量配置
cat conf/.env

# 查看详细错误日志
python api.py
```

#### 数据库相关问题
```bash
# 检查数据目录权限
ls -la data/

# 手动初始化数据库
python -c "from biz.service.review_service import ReviewService; ReviewService.init_db()"
```

### 3. Docker 相关问题

#### 构建失败
```bash
# 查看构建日志
docker-compose build --no-cache

# 检查 Docker 镜像
docker images | grep ai-codereview
```

#### 容器运行问题
```bash
# 查看容器日志
docker-compose logs app

# 进入容器调试
docker-compose exec app sh

# 检查容器内服务状态
docker-compose exec app supervisorctl status
```

## 性能优化建议

### 1. 前端优化
- 启用 Nginx gzip 压缩（已配置）
- 配置静态资源缓存（已配置）
- 考虑实现分页加载大量数据

### 2. 后端优化
- 配置 Redis 缓存（可选）
- 实施数据库索引优化
- 配置连接池

### 3. 部署优化
- 使用 HTTPS（推荐）
- 配置负载均衡（如需要）
- 设置监控和告警

## 迁移说明

### 从原 Streamlit 版本迁移

1. **数据兼容性**: 新版本完全兼容原有的 SQLite 数据库
2. **配置文件**: `.env` 配置文件保持向后兼容
3. **Webhook**: Webhook URL 和配置保持不变
4. **Docker**: 端口从 5002 (Streamlit) 改为 80 (Nginx)

### 回滚到原版本

如果需要回滚到原 Streamlit 版本：

```bash
# 检出到之前的提交
git checkout [previous-commit-hash]

# 重新构建和部署
docker-compose up -d --build
```

## 支持和反馈

如遇到问题或需要支持：

1. 查看 [CLAUDE.md](./CLAUDE.md) 了解架构详情
2. 检查项目的 Issues 页面
3. 查看容器日志进行问题诊断

---

**注意**: 这是一个重大架构更新，请在生产环境部署前在测试环境充分验证所有功能。