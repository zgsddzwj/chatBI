"""Schema 数据访问仓库。

封装对 schema 元数据的访问，隔离底层存储细节。
"""
from __future__ import annotations

from typing import Any

from app.schema_meta import BUSINESS_SCHEMA


class SchemaRepository:
    """Schema 元数据仓库。"""

    def get_schema(self) -> dict[str, Any]:
        """获取完整 Schema。"""
        return BUSINESS_SCHEMA

    def get_tables(self) -> list[dict[str, Any]]:
        """获取所有表定义。"""
        return BUSINESS_SCHEMA["tables"]

    def get_table_by_name(self, name: str) -> dict[str, Any] | None:
        """根据表名获取表定义。"""
        for table in BUSINESS_SCHEMA["tables"]:
            if table["name"] == name:
                return table
        return None

    def get_relations(self) -> list[str]:
        """获取表关系定义。"""
        return BUSINESS_SCHEMA["relations"]

    def get_hints(self) -> list[str]:
        """获取业务提示。"""
        return BUSINESS_SCHEMA["hints"]
