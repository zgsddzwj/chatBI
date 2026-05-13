"""元信息接口：schema、示例问题等。"""
from __future__ import annotations

from fastapi import APIRouter

from app.schema_meta import BUSINESS_SCHEMA
from app.schemas import SampleQuestions, SchemaInfo

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
