#!/bin/bash

echo "🚀 启动 AI代码审查平台 Vue3 前端"
echo "=================================="

# 检查 Node.js 是否安装
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js (版本 >= 16)"
    exit 1
fi

# 检查 npm 是否安装
if ! command -v npm &> /dev/null; then
    echo "❌ npm 未安装，请先安装 npm"
    exit 1
fi

echo "✅ Node.js 版本: $(node --version)"
echo "✅ npm 版本: $(npm --version)"

# 检查是否存在 node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 安装依赖..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
    echo "✅ 依赖安装完成"
else
    echo "✅ 依赖已存在"
fi

echo ""
echo "🌐 启动开发服务器..."
echo "访问地址: http://localhost:3000"
echo "默认用户名: admin"
echo "默认密码: admin"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

# 启动开发服务器
npm run dev
