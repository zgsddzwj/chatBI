.PHONY: deploy down logs test smoke dev dev-backend dev-frontend check

# ========== Docker 生产部署 ==========

# 一键部署
deploy:
	@echo "==> 构建并启动 ChatBI..."
	docker compose up -d --build
	@echo "==> 等待服务就绪..."
	@sleep 5
	@echo "==> 健康检查..."
	@curl -fsS http://localhost:8000/health > /dev/null && echo "后端 ✓" || echo "后端 ✗"
	@curl -fsS http://localhost:8080 > /dev/null && echo "前端 ✓" || echo "前端 ✗"
	@echo "==> 部署完成"

# 停止
down:
	docker compose down

# 查看日志
logs:
	docker compose logs -f

# ========== 本地开发 ==========

# 一键启动本地开发环境（后端 + 前端）
dev:
	@echo "==> 启动本地开发环境..."
	@echo "==> 1. 检查环境..."
	@which uv > /dev/null || (echo "错误: 未安装 uv (https://docs.astral.sh/uv/)" && exit 1)
	@which npm > /dev/null || (echo "错误: 未安装 npm" && exit 1)
	@echo "==> 2. 启动后端 (http://localhost:8000)..."
	@cd backend && uv sync > /dev/null 2>&1
	@cd backend && (uv run uvicorn app.main:app --reload --port 8000 &)
	@echo "==> 3. 启动前端 (http://localhost:5173)..."
	@cd frontend && (npm run dev &)
	@echo "==> 4. 等待服务启动..."
	@sleep 3
	@$(MAKE) check
	@echo "==> 开发环境已启动!"
	@echo "   后端: http://localhost:8000"
	@echo "   前端: http://localhost:5173"
	@echo "   API文档: http://localhost:8000/docs"

# 仅启动后端
dev-backend:
	@echo "==> 启动后端开发服务器..."
	cd backend && uv run uvicorn app.main:app --reload --port 8000

# 仅启动前端
dev-frontend:
	@echo "==> 启动前端开发服务器..."
	cd frontend && npm run dev

# ========== 测试与健康检查 ==========

# 运行测试
test:
	cd backend && uv run pytest -q --no-cov -k "not stream"

# 完整测试（含覆盖率）
test-cov:
	cd backend && uv run pytest -q

# 健康检查
check:
	@echo "==> 健康检查..."
	@curl -fsS http://localhost:8000/health > /dev/null 2>&1 && echo "后端 health ✓" || echo "后端 health ✗"
	@curl -fsS http://localhost:8000/ready > /dev/null 2>&1 && echo "后端 ready  ✓" || echo "后端 ready  ✗"
	@curl -fsS http://localhost:5173 > /dev/null 2>&1 && echo "前端       ✓" || echo "前端       ✗"

# Smoke 测试
smoke:
	@curl -fsS http://localhost:8000/health | jq .
	@curl -fsS http://localhost:8000/ready | jq .
