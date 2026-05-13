#!/usr/bin/env bash
# ChatBI 一键部署：准备 .env 并启动 Docker Compose
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "[deploy] 已从 .env.example 创建 .env，请填写 DEEPSEEK_API_KEY 后再次执行："
  echo "         bash scripts/deploy.sh   或   make deploy   或   docker compose up -d --build"
  exit 1
fi

if ! grep -qE '^DEEPSEEK_API_KEY=.' .env; then
  echo "[deploy] .env 中 DEEPSEEK_API_KEY 为空或无效，请填写 DeepSeek（或其它兼容端点）的 API Key。"
  exit 1
fi

echo "[deploy] 构建并启动服务…"
docker compose up -d --build

HTTP_PORT="8080"
BACKEND_PUBLISH_PORT="8000"
if grep -qE '^HTTP_PORT=' .env; then
  HTTP_PORT="$(grep -E '^HTTP_PORT=' .env | tail -1 | cut -d= -f2- | tr -d ' \r')"
fi
if grep -qE '^BACKEND_PUBLISH_PORT=' .env; then
  BACKEND_PUBLISH_PORT="$(grep -E '^BACKEND_PUBLISH_PORT=' .env | tail -1 | cut -d= -f2- | tr -d ' \r')"
fi

echo ""
echo "[deploy] 完成。"
echo "  · 对话界面:  http://127.0.0.1:${HTTP_PORT}/"
echo "  · API 文档:  http://127.0.0.1:${BACKEND_PUBLISH_PORT}/docs"
echo "  · 健康检查:  http://127.0.0.1:${BACKEND_PUBLISH_PORT}/health"
echo ""
echo "查看日志: docker compose logs -f --tail=200"
echo "停止服务: docker compose down"
