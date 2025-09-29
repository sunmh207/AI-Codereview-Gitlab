.PHONY: build run clean test docker-build docker-run frontend-build frontend-dev

# 构建后端
build:
	go build -o ai-codereview .

# 运行后端
run:
	go run .

# 清理构建文件
clean:
	rm -f ai-codereview
	rm -rf frontend/dist

# 运行测试
test:
	go test ./...

# 构建前端
frontend-build:
	cd frontend && npm install && npm run build

# 前端开发模式
frontend-dev:
	cd frontend && npm run dev

# 构建Docker镜像
docker-build:
	docker build -t ai-codereview .

# 运行Docker容器
docker-run:
	docker-compose up -d

# 停止Docker容器
docker-stop:
	docker-compose down

# 完整构建（前端+后端）
build-all: frontend-build build

# 开发环境启动
dev:
	make frontend-dev &
	make run

# 生产环境部署
deploy: build-all docker-build docker-run