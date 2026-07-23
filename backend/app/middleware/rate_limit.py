"""简易内存速率限制中间件。"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """按 IP 对 /api/chat 路径限流。"""

    # 每隔多少次请求做一次过期清理，避免 _hits 字典无限膨胀
    _CLEUP_INTERVAL = 100

    def __init__(self, app, max_requests: int = 30, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()
        self._request_count = 0

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _is_limited(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            # 定期清理所有过期 IP 记录，防止内存泄漏
            self._request_count += 1
            if self._request_count >= self._CLEUP_INTERVAL:
                self._request_count = 0
                stale_keys = [
                    k for k, ts in self._hits.items()
                    if not ts or ts[-1] <= cutoff
                ]
                for k in stale_keys:
                    del self._hits[k]

            hits = [t for t in self._hits[key] if t > cutoff]
            if len(hits) >= self.max_requests:
                self._hits[key] = hits
                return True
            hits.append(now)
            self._hits[key] = hits
            return False

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if request.method == "POST" and path.startswith("/api/chat"):
            if self._is_limited(self._client_key(request)):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "请求过于频繁，请稍后再试"},
                )
        return await call_next(request)
