import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    embedding_client_manager.init()
    qdrant_client_manager.init()
    es_client_manager.init()
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()
    
    # 缓存预热
    try:
        from app.services.cache_v2 import warmup_cache
        warmed = warmup_cache()
        logger.info("Cache warmup completed: %d queries warmed", warmed)
    except Exception as exc:
        logger.warning("Cache warmup failed: %s", exc)
    
    yield

    # 按初始化的逆序关闭资源，避免依赖冲突
    # 先关业务连接，再关搜索引擎，最后关向量库
    shutdown_errors: list[str] = []
    for name, manager in [
        ("dw_mysql", dw_mysql_client_manager),
        ("meta_mysql", meta_mysql_client_manager),
        ("es", es_client_manager),
        ("qdrant", qdrant_client_manager),
    ]:
        try:
            await manager.close()
        except Exception as exc:  # noqa: BLE001
            shutdown_errors.append(f"{name}: {exc}")
            logger.warning("关闭 %s 客户端失败: %s", name, exc)

    if shutdown_errors:
        logger.error("部分资源关闭失败: %s", "; ".join(shutdown_errors))
