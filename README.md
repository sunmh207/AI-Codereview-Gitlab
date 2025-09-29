# AI代码审查系统 - Vue.js前后端分离版

基于AI的GitLab/GitHub代码审查系统，采用Vue.js + Flask前后端分离架构。

## 🏗️ 系统架构

- **前端**: Vue.js 3 + TypeScript + Element Plus + Vite
- **后端**: Flask + Python 3.11
- **数据库**: MySQL
- **消息队列**: Redis + RQ
- **AI模型**: 支持OpenAI、智谱AI、Ollama等多种LLM

## 🚀 快速启动

### 方式一：使用启动脚本（推荐）

```bash
# 克隆项目
git clone <repository-url>
cd AI-Codereview-Gitlab

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置

# 一键启动前后端
./start.sh
```

### 方式二：手动启动

#### 1. 启动后端服务

```bash
# 安装Python依赖
pip install -r requirements.txt

# 启动Flask API服务
python api.py
```

后端服务将在 http://localhost:5001 启动

#### 2. 启动前端服务

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务将在 http://localhost:3000 启动

### 方式三：Docker部署

```bash
# 构建并启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 📁 项目结构

```
AI-Codereview-Gitlab/
├── frontend/                 # Vue.js前端
│   ├── src/
│   │   ├── api/             # API接口
│   │   ├── components/      # Vue组件
│   │   ├── views/           # 页面视图
│   │   ├── router/          # 路由配置
│   │   └── stores/          # 状态管理
│   ├── package.json
│   └── vite.config.ts
├── biz/                     # 业务逻辑层
│   ├── service/            # 业务服务
│   ├── entity/             # 实体模型
│   ├── gitlab/             # GitLab集成
│   ├── github/             # GitHub集成
│   └── llm/                # LLM集成
├── api.py                  # Flask API服务器
├── start.sh               # 一键启动脚本
├── Dockerfile             # Docker构建文件
├── docker-compose.yml     # Docker编排文件
└── requirements.txt       # Python依赖
```

## 🔧 配置说明

### 环境变量配置

复制 `.env.example` 为 `.env` 并配置以下变量：

```bash
# 数据库配置
DATABASE_URL=mysql://user:password@localhost:3306/ai_codereview

# Redis配置
REDIS_URL=redis://localhost:6379/0

# GitLab配置
GITLAB_URL=https://gitlab.example.com
GITLAB_TOKEN=your_gitlab_token

# GitHub配置（可选）
GITHUB_TOKEN=your_github_token

# LLM配置
LLM_PROVIDER=openai  # 支持: openai, zhipu, ollama
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1

# JWT配置
JWT_SECRET_KEY=your_jwt_secret
```

### 前端代理配置

前端开发时，API请求会自动代理到后端服务：

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true
      }
    }
  }
})
```

## 🎯 功能特性

- ✅ **代码审查**: 自动分析MR/PR中的代码变更
- ✅ **多平台支持**: 同时支持GitLab和GitHub
- ✅ **多LLM支持**: OpenAI、智谱AI、Ollama等
- ✅ **实时统计**: 审查数据可视化展示
- ✅ **用户认证**: JWT token认证机制
- ✅ **响应式UI**: 基于Element Plus的现代化界面
- ✅ **Docker部署**: 支持容器化部署

## 🔄 API接口

### 认证相关
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/verify` - 验证token

### 数据统计
- `GET /api/metadata` - 获取元数据统计
- `GET /api/statistics/projects` - 项目统计数据
- `GET /api/reviews/mr` - MR审查记录
- `GET /api/reviews/push` - Push审查记录

## 🛠️ 开发指南

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 代码检查
npm run lint
```

### 后端开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 启动开发服务器
python api.py

# 运行测试
python -m pytest tests/
```

## 📦 部署说明

### 生产环境部署

1. **构建前端**:
```bash
cd frontend
npm run build
```

2. **配置环境变量**:
```bash
export FLASK_ENV=production
export DATABASE_URL=mysql://...
```

3. **启动服务**:
```bash
# 使用gunicorn启动
gunicorn -w 4 -b 0.0.0.0:5001 api:app
```

### Docker部署

```bash
# 构建镜像
docker build -t ai-codereview .

# 运行容器
docker run -d -p 5001:5001 --env-file .env ai-codereview
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 故障排除

### 常见问题

1. **前端无法连接后端**
   - 检查后端服务是否启动在5001端口
   - 确认vite.config.ts中的代理配置正确

2. **数据库连接失败**
   - 检查DATABASE_URL配置
   - 确认MySQL服务正在运行

3. **LLM调用失败**
   - 检查API密钥配置
   - 确认网络连接正常

### 日志查看

```bash
# 查看后端日志
tail -f log/app.log

# 查看Docker日志
docker-compose logs -f
```

## 📞 联系方式

如有问题或建议，请提交Issue或联系维护者。