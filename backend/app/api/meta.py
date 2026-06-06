"""元信息接口：schema、示例问题等。"""
from __future__ import annotations

from fastapi import APIRouter

from app.schema_meta import BUSINESS_SCHEMA
from app.schemas import SampleQuestions, SchemaInfo
from app.services.hybrid_search import hybrid_search

router = APIRouter(prefix="/api/meta", tags=["meta"])


SAMPLE_QUESTIONS = [
    "2024 年每个月的销售额是多少？",
    "销售额排名前 5 的商品是哪些？",
    "各地区的用户数量分布如何？",
    "不同下单渠道的订单量对比",
    "2025 年第一季度的退款率是多少？",
    "每个商品类别的总营收和总利润",
    "最近 6 个月各渠道的销售额趋势",
    "哪个年龄段的用户消费最多？",
]


@router.get("/schema", response_model=SchemaInfo)
def get_schema() -> dict:
    return BUSINESS_SCHEMA


@router.get("/samples", response_model=SampleQuestions)
def get_samples() -> dict:
    return {"questions": SAMPLE_QUESTIONS}


@router.get("/search")
def search_schema(q: str, top_k: int = 5) -> dict:
    """混合检索调试接口：测试全文+向量检索效果。"""
    results = hybrid_search(q, top_k=top_k)
    return {
        "query": q,
        "results": [
            {
                "id": r["id"],
                "score": r["score"],
                "type": "hint" if r.get("is_hint") else "table",
                "table": r["table_data"]["name"] if r["table_data"] else None,
            }
            for r in results
        ],
    }
