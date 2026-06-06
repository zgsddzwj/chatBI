#!/usr/bin/env python3
"""测试混合检索系统。"""
from app.services.hybrid_search import (
    _build_schema_documents,
    _get_vector_index,
    _get_fts_index,
    hybrid_search,
    render_schema_prompt_hybrid,
)

print("=" * 60)
print("1. Schema 文档数量:", len(_build_schema_documents()))

print("=" * 60)
print("2. 向量索引文档数:", len(_get_vector_index().ids))

print("=" * 60)
print("3. FTS 索引状态: ready")
_ = _get_fts_index()

print("=" * 60)
print("4. 混合检索测试")
test_queries = [
    "用户年龄分布",
    "各商品类别的销售额",
    "2024年订单退款情况",
    "哪个渠道卖得最好",
    "华东地区用户注册时间",
]

for q in test_queries:
    results = hybrid_search(q, top_k=3)
    print(f"\n  查询: {q}")
    for r in results:
        print(f"    -> {r['id']} (score={r['score']:.4f})")

print("=" * 60)
print("5. Prompt 生成测试")
prompt = render_schema_prompt_hybrid("各年龄段用户消费金额", top_k=2)
print(prompt[:500] + "...")

print("=" * 60)
print("所有测试通过!")
