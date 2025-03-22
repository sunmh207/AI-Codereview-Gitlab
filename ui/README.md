# AI Code Review UI

这是一个基于Vue 3开发的AI代码审查系统的前端界面。

## 技术栈

- Vue 3
- Vue Router
- Element Plus
- Bootstrap 5
- Chart.js
- Axios

## 开发环境要求

- Node.js >= 14.0.0
- npm >= 6.0.0

## 安装

```bash
# 安装依赖
npm install
```

## 开发

```bash
# 启动开发服务器
npm run serve
```

## 构建

```bash
# 构建生产环境代码
npm run build
```

## 代码检查

```bash
# 运行代码检查
npm run lint
```

## 环境变量配置

项目包含以下环境配置文件：

- `.env` - 默认环境变量
- `.env.development` - 开发环境变量
- `.env.production` - 生产环境变量

## 项目结构

```
ui/
├── src/                # 源代码目录
├── public/            # 静态资源目录
├── dist/              # 构建输出目录
├── node_modules/      # 依赖包目录
└── package.json       # 项目配置文件
```

## 开发规范

- 使用ESLint进行代码规范检查
- 遵循Vue 3组合式API的开发风格
- 使用Element Plus组件库进行界面开发 