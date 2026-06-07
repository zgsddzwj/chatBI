"""元数据数据库模型：table_info, column_info, metric_info, column_metric。

对应文档中元数据知识库的四张表。
"""
from __future__ import annotations

from sqlalchemy import JSON, Column, String, Text
from sqlalchemy.orm import declarative_base

MetaBase = declarative_base()


class TableInfoMySQL(MetaBase):
    __tablename__ = "table_info"

    id = Column(String(64), primary_key=True, comment="表编号")
    name = Column(String(128), comment="表名称")
    role = Column(String(32), comment="表类型(fact/dim)")
    description = Column(Text, comment="表描述")


class ColumnInfoMySQL(MetaBase):
    __tablename__ = "column_info"

    id = Column(String(64), primary_key=True, comment="列编号")
    name = Column(String(128), comment="列名称")
    type = Column(String(64), comment="数据类型")
    role = Column(String(32), comment="列类型(primary_key,foreign_key,measure,dimension)")
    examples = Column(JSON, comment="数据示例")
    description = Column(Text, comment="列描述")
    alias = Column(JSON, comment="列别名")
    table_id = Column(String(64), comment="所属表编号")


class MetricInfoMySQL(MetaBase):
    __tablename__ = "metric_info"

    id = Column(String(64), primary_key=True, comment="指标编码")
    name = Column(String(128), comment="指标名称")
    description = Column(Text, comment="指标描述")
    relevant_columns = Column(JSON, comment="关联字段")
    alias = Column(JSON, comment="指标别名")


class ColumnMetricMySQL(MetaBase):
    __tablename__ = "column_metric"

    column_id = Column(String(64), primary_key=True, comment="列编号")
    metric_id = Column(String(64), primary_key=True, comment="指标编号")
