"""元信息接口：schema、示例问题等（已适配新版数仓表结构）。"""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas import SampleQuestions

router = APIRouter(prefix="/api/meta", tags=["meta"])

# 新版示例问题（基于 dim_region/dim_customer/dim_product/dim_date/fact_order）
SAMPLE_QUESTIONS = [
    "2024 年每个月的销售额是多少？",
    "销售额排名前 5 的商品是哪些？",
    "各地区的订单数量分布如何？",
    "不同商品品类的销售额对比",
    "2025 年第一季度的总销售额是多少？",
    "每个商品品牌的总营收和总销量",
    "最近 6 个月各地区的销售额趋势",
    "哪个会员等级的客户消费最多？",
]


@router.get("/schema")
def get_schema() -> dict:
    """返回新版数仓表结构（文档要求的 5 张表）。"""
    return {
        "dialect": "sqlite",
        "tables": [
            {
                "name": "dim_region",
                "comment": "地区维度表",
                "columns": [
                    {"name": "region_id", "type": "TEXT", "comment": "地区ID（主键）"},
                    {"name": "province", "type": "TEXT", "comment": "省份"},
                    {"name": "region_name", "type": "TEXT", "comment": "大区名称（华东、华南等）"},
                    {"name": "country", "type": "TEXT", "comment": "国家"},
                ],
            },
            {
                "name": "dim_customer",
                "comment": "客户维度表",
                "columns": [
                    {"name": "customer_id", "type": "TEXT", "comment": "客户ID（主键）"},
                    {"name": "customer_name", "type": "TEXT", "comment": "客户姓名"},
                    {"name": "gender", "type": "TEXT", "comment": "性别"},
                    {"name": "member_level", "type": "TEXT", "comment": "会员等级"},
                ],
            },
            {
                "name": "dim_product",
                "comment": "商品维度表",
                "columns": [
                    {"name": "product_id", "type": "TEXT", "comment": "商品ID（主键）"},
                    {"name": "product_name", "type": "TEXT", "comment": "商品名称"},
                    {"name": "category", "type": "TEXT", "comment": "商品品类"},
                    {"name": "brand", "type": "TEXT", "comment": "品牌"},
                ],
            },
            {
                "name": "dim_date",
                "comment": "时间维度表",
                "columns": [
                    {"name": "date_id", "type": "TEXT", "comment": "日期ID（主键，格式yyyyMMdd）"},
                    {"name": "year", "type": "INTEGER", "comment": "年份"},
                    {"name": "quarter", "type": "TEXT", "comment": "季度"},
                    {"name": "month", "type": "INTEGER", "comment": "月份"},
                    {"name": "day", "type": "INTEGER", "comment": "日"},
                ],
            },
            {
                "name": "fact_order",
                "comment": "订单事实表",
                "columns": [
                    {"name": "order_id", "type": "TEXT", "comment": "订单ID（主键）"},
                    {"name": "customer_id", "type": "TEXT", "comment": "客户ID，关联 dim_customer"},
                    {"name": "product_id", "type": "TEXT", "comment": "商品ID，关联 dim_product"},
                    {"name": "date_id", "type": "TEXT", "comment": "日期ID，关联 dim_date"},
                    {"name": "region_id", "type": "TEXT", "comment": "地区ID，关联 dim_region"},
                    {"name": "order_quantity", "type": "INTEGER", "comment": "购买数量"},
                    {"name": "order_amount", "type": "REAL", "comment": "订单金额"},
                ],
            },
        ],
        "relations": [
            "fact_order.customer_id -> dim_customer.customer_id",
            "fact_order.product_id -> dim_product.product_id",
            "fact_order.date_id -> dim_date.date_id",
            "fact_order.region_id -> dim_region.region_id",
        ],
        "hints": [
            "时间范围筛选请使用 dim_date.date_id（格式 yyyyMMdd）或 dim_date.year/month",
            "金额相关分析请使用 fact_order.order_amount",
            "数量相关分析请使用 fact_order.order_quantity",
            "地区分析请使用 dim_region.region_name 或 dim_region.province",
            "客户分析请使用 dim_customer.member_level 或 dim_customer.gender",
            "商品分析请使用 dim_product.category 或 dim_product.brand",
        ],
    }


@router.get("/samples", response_model=SampleQuestions)
def get_samples() -> dict:
    return {"questions": SAMPLE_QUESTIONS}


@router.get("/search")
def search_schema(q: str, top_k: int = 5) -> dict:
    """混合检索调试接口（已废弃，新版使用 Qdrant + ES）。"""
    return {
        "query": q,
        "message": "该接口已废弃，新版检索通过 /api/query 内部调用 Qdrant + ES 完成。",
        "results": [],
    }


# ========== 缓存管理接口 ==========

@router.get("/cache/stats")
def get_cache_stats() -> dict:
    """获取查询缓存统计信息。"""
    from app.services.cache_v2 import get_cache_stats
    return get_cache_stats()


@router.post("/cache/clear")
def clear_cache() -> dict:
    """清空所有查询缓存。"""
    from app.services.cache_v2 import clear_all_cache
    count = clear_all_cache()
    return {"cleared": count, "message": f"已清空 {count} 条缓存"}


@router.get("/cache/similar")
def find_similar_cache(q: str, limit: int = 3) -> dict:
    """查找相似的历史查询（语义缓存）。"""
    from app.services.cache_v2 import find_similar_queries
    results = find_similar_queries(q, limit)
    return {"query": q, "similar_queries": results}
