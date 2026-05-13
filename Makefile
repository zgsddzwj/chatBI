.PHONY: deploy down logs ps pull

# 一键部署（需已配置 .env 中的 DEEPSEEK_API_KEY）
deploy:
	@bash scripts/deploy.sh

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

pull:
	docker compose pull
