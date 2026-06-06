"""元数据知识库自动构建服务。

从配置的数据源自动抽取 schema 信息，构建：
1. 向量索引（语义搜索）
2. FTS5 全文索引（关键词搜索）

触发方式：
- 数据源创建/更新时自动触发
- 提供 /api/datasources/{id}/sync-schema 手动触发
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import Engine, create_engine, inspect, text

from app.config import get_settings
from app.database import app_engine
from app.services.hybrid_search import _build_schema_documents, _get_fts_index, _get_vector_index

logger = logging.getLogger(__name__)


def _get_engine_for_source(source_id: int) -> Engine | None:
    """获取数据源的 SQLAlchemy 引擎。"""
    with app_engine.begin() as conn:
        row = conn.execute(
            text("SELECT connection_url FROM data_sources WHERE id = :id AND is_active = 1"),
            {"id": source_id},
        ).fetchone()
    if not row:
        return None
    url = row[0]
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


def _extract_schema_from_engine(engine: Engine) -> dict[str, Any]:
    """从数据库引擎抽取 Schema 信息。"""
    inspector = inspect(engine)
    tables = []

    for table_name in inspector.get_table_names():
        columns = []
        for col in inspector.get_columns(table_name):
            columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "comment": col.get("comment", ""),
            })

        # 获取外键关系
        fks = inspector.get_foreign_keys(table_name)
        table_comment = ""
        try:
            # 尝试获取表注释（SQLite 不支持，PostgreSQL/MySQL 支持）
            with engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT obj_description('{table_name}'::regclass)")
                ).fetchone()
                if result and result[0]:
                    table_comment = result[0]
        except Exception:
            pass

        tables.append({
            "name": table_name,
            "comment": table_comment or f"{table_name} 表",
            "columns": columns,
            "foreign_keys": fks,
        })

    # 构建关系
    relations = []
    for table in tables:
        for fk in table.get("foreign_keys", []):
            referred_table = fk.get("referred_table")
            referred_columns = fk.get("referred_columns", [])
            constrained_columns = fk.get("constrained_columns", [])
            if referred_table and constrained_columns and referred_columns:
                relations.append(
                    f"{table['name']}.{constrained_columns[0]} -> {referred_table}.{referred_columns[0]}"
                )

    # 获取数据库方言
    dialect = engine.dialect.name

    return {
        "dialect": dialect,
        "tables": tables,
        "relations": relations,
        "hints": [],
    }


def build_schema_for_source(source_id: int) -> dict[str, Any]:
    """为指定数据源构建 Schema 知识库。

    Args:
        source_id: 数据源 ID

    Returns:
        构建结果
    """
    logger.info("开始为数据源 %d 构建 Schema 知识库", source_id)

    engine = _get_engine_for_source(source_id)
    if not engine:
        return {"ok": False, "error": "数据源不存在或未激活"}

    try:
        schema = _extract_schema_from_engine(engine)
    except Exception as exc:
        logger.exception("抽取 Schema 失败: %s", exc)
        return {"ok": False, "error": str(exc)}
    finally:
        engine.dispose()

    # 保存到数据源配置
    with app_engine.begin() as conn:
        conn.execute(
            text("UPDATE data_sources SET schema_json = :schema WHERE id = :id"),
            {"schema": json.dumps(schema, ensure_ascii=False), "id": source_id},
        )

    logger.info("数据源 %d Schema 构建完成: %d 张表", source_id, len(schema["tables"]))
    return {
        "ok": True,
        "tables_count": len(schema["tables"]),
        "relations_count": len(schema["relations"]),
    }


def rebuild_hybrid_index() -> dict[str, Any]:
    """重建混合检索索引。

    基于当前 BUSINESS_SCHEMA 重建向量索引和全文索引。
    未来可扩展为基于多数据源的 schema 合并重建。
    """
    logger.info("开始重建混合检索索引")

    try:
        docs = _build_schema_documents()

        # 重建向量索引
        vector_idx = _get_vector_index()
        # 清空并重建
        vector_idx.vectors = None
        vector_idx.ids = []
        vector_idx.doc_map = {}

        from app.services.hybrid_search import _get_embedding
        for doc in docs:
            vector = _get_embedding(doc["embedding_text"])
            vector_idx.add(doc["id"], vector, doc)

        from app.services.hybrid_search import VECTOR_CACHE
        vector_idx.save(VECTOR_CACHE)
        logger.info("向量索引重建完成: %d 个文档", len(vector_idx.ids))

        # 重建全文索引
        fts_idx = _get_fts_index()
        fts_idx.rebuild(docs)
        logger.info("全文索引重建完成")

        return {
            "ok": True,
            "vector_docs": len(vector_idx.ids),
            "fts_docs": len(docs),
        }
    except Exception as exc:
        logger.exception("重建索引失败: %s", exc)
        return {"ok": False, "error": str(exc)}
