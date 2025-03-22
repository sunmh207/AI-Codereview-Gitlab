#!/bin/bash

# 输出颜色设置
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始构建前端项目...${NC}"

# 检查ui目录是否存在
if [ ! -d "ui" ]; then
    echo -e "${RED}错误：ui目录不存在${NC}"
    exit 1
fi

# 进入前端项目目录
cd ui

# 检查package.json是否存在
if [ ! -f "package.json" ]; then
    echo -e "${RED}错误：package.json不存在${NC}"
    exit 1
fi

# 检查src目录是否存在
if [ ! -d "src" ]; then
    echo -e "${RED}错误：src目录不存在${NC}"
    exit 1
fi

# 检查main.js是否存在
if [ ! -f "src/main.js" ]; then
    echo -e "${RED}错误：src/main.js不存在${NC}"
    exit 1
fi

# 检查是否安装了依赖
if [ ! -d "node_modules" ]; then
    echo -e "${GREEN}安装依赖...${NC}"
    npm install || yarn install
fi

# 构建项目
echo -e "${GREEN}构建项目...${NC}"
npm run build || yarn build

# 检查构建是否成功
if [ $? -eq 0 ]; then
    echo -e "${GREEN}构建成功！${NC}"
    
    # 检查dist目录是否存在
    if [ ! -d "dist" ]; then
        echo -e "${RED}错误：构建输出目录dist不存在${NC}"
        exit 1
    fi
    
    # 创建后端静态文件目录（如果不存在）
    mkdir -p ../static

    # 复制构建文件到后端目录
    echo -e "${GREEN}复制构建文件到后端目录...${NC}"
    cp -r dist/* ../static/

    echo -e "${GREEN}前端构建和部署完成！${NC}"
else
    echo -e "${RED}构建失败，请检查错误信息${NC}"
    exit 1
fi 