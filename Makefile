.PHONY: deploy down logs test smoke

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

# 运行测试
test:
	cd backend && uv run pytest -q

# Smoke 测试
smoke:
	@curl -fsS http://localhost:8000/health | jq .
	@curl -fsS http://localhost:8000/ready | jq .
