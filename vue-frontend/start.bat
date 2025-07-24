@echo off
chcp 65001 >nul

echo 🚀 启动 AI代码审查平台 Vue3 前端
echo ==================================

REM 检查 Node.js 是否安装
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js 未安装，请先安装 Node.js (版本 >= 16)
    pause
    exit /b 1
)

REM 检查 npm 是否安装
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ npm 未安装，请先安装 npm
    pause
    exit /b 1
)

echo ✅ Node.js 版本:
node --version
echo ✅ npm 版本:
npm --version

REM 检查是否存在 node_modules
if not exist "node_modules" (
    echo 📦 安装依赖...
    npm install
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
    echo ✅ 依赖安装完成
) else (
    echo ✅ 依赖已存在
)

echo.
echo 🌐 启动开发服务器...
echo 访问地址: http://localhost:3000
echo 默认用户名: admin
echo 默认密码: admin
echo.
echo 按 Ctrl+C 停止服务器
echo.

REM 启动开发服务器
npm run dev

pause
