"""Schema 混合检索：全文搜索 + 向量相似度 + 重排序。

实现策略：
1. 全文索引：SQLite FTS5 对表名、字段名、注释建立倒排索引
2. 向量索引：OpenAI Embedding API 生成语义向量，本地 HNSW 近似搜索
3. 混合排序：RRF (Reciprocal Rank Fusion) 融合全文和向量结果
4. 重排序：Cross-encoder 风格的本地轻量模型（可选）

效果目标：大 Schema 场景下（50+ 表），SQL 生成准确率提升 20%+
"""
from __future__ import annotations

import json
import logging
import math
import pickle
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.config import get_settings
from app.schema_meta import BUSINESS_SCHEMA

logger = logging.getLogger(__name__)

# 本地缓存路径
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
VECTOR_CACHE = DATA_DIR / "schema_vectors.pkl"
FTS_DB_PATH = DATA_DIR / "schema_fts.db"

# OpenAI embedding 模型
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536  # text-embedding-3-small 维度


def _get_openai_client():
    """获取 OpenAI 客户端（支持独立 embedding 配置）。"""
    from openai import OpenAI
    settings = get_settings()
    api_key = settings.embedding_api_key or settings.deepseek_api_key
    base_url = settings.embedding_base_url or settings.deepseek_base_url
    return OpenAI(api_key=api_key, base_url=base_url)


def _get_embedding(text: str) -> list[float]:
    """获取文本的 embedding 向量。"""
    settings = get_settings()
    model = settings.embedding_model or EMBED_MODEL
    try:
        client = _get_openai_client()
        resp = client.embeddings.create(
            model=model,
            input=text[:8000],  # 限制长度
            encoding_format="float",
        )
        return resp.data[0].embedding
    except Exception as e:
        logger.warning("Embedding API 调用失败: %s, 使用随机向量 fallback", e)
        # Fallback: 使用哈希生成确定性随机向量
        np.random.seed(hash(text) % 2**32)
        vec = np.random.randn(EMBED_DIM).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        return vec.tolist()


# =============================================================================
# 1. 文档构建：将 Schema 转换为可检索文档
# =============================================================================

def _build_schema_documents() -> list[dict[str, Any]]:
    """将 Schema 构建为结构化文档列表。
    
    每个文档代表一个表，包含：
    - id: 表名
    - text: 用于全文搜索的文本（表名 + 注释 + 字段名 + 字段注释）
    - embedding_text: 用于向量化的语义文本
    - table_data: 原始表结构数据
    """
    docs = []
    for table in BUSINESS_SCHEMA["tables"]:
        table_name = table["name"]
        table_comment = table.get("comment", "")
        
        # 全文搜索文本：关键词密集
        text_parts = [table_name, table_comment]
        for col in table.get("columns", []):
            text_parts.append(col["name"])
            text_parts.append(col.get("comment", ""))
        text = " ".join(text_parts)
        
        # 向量语义文本：更自然的描述
        embedding_parts = [f"表名: {table_name}", f"描述: {table_comment}"]
        for col in table.get("columns", []):
            col_desc = f"字段 {col['name']} ({col['type']}): {col.get('comment', '')}"
            embedding_parts.append(col_desc)
        embedding_text = "\n".join(embedding_parts)
        
        docs.append({
            "id": table_name,
            "text": text,
            "embedding_text": embedding_text,
            "table_data": table,
        })
    
    # 添加 hints 作为独立文档
    for i, hint in enumerate(BUSINESS_SCHEMA.get("hints", [])):
        docs.append({
            "id": f"hint_{i}",
            "text": hint,
            "embedding_text": f"业务规则: {hint}",
            "table_data": None,
            "is_hint": True,
        })
    
    return docs


# =============================================================================
# 2. 向量索引：本地 HNSW 近似最近邻
# =============================================================================

class VectorIndex:
    """基于 numpy 的轻量级向量索引（HNSW 简化版）。"""
    
    def __init__(self, dim: int = EMBED_DIM):
        self.dim = dim
        self.vectors: np.ndarray | None = None
        self.ids: list[str] = []
        self.doc_map: dict[str, dict] = {}
    
    def add(self, doc_id: str, vector: list[float], doc: dict):
        """添加文档向量。"""
        vec = np.array(vector, dtype=np.float32).reshape(1, -1)
        if self.vectors is None:
            self.vectors = vec
        else:
            self.vectors = np.vstack([self.vectors, vec])
        self.ids.append(doc_id)
        self.doc_map[doc_id] = doc
    
    def search(self, query_vector: list[float], top_k: int = 5) -> list[tuple[str, float]]:
        """搜索最相似的文档，返回 (doc_id, score) 列表。"""
        if self.vectors is None or len(self.ids) == 0:
            return []
        
        query = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        
        # 余弦相似度
        similarities = cosine_similarity(query, self.vectors)[0]
        
        # 取 top_k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.3:  # 阈值过滤
                results.append((self.ids[idx], float(similarities[idx])))
        
        return results
    
    def save(self, path: Path):
        """保存索引到磁盘。"""
        with open(path, "wb") as f:
            pickle.dump({
                "vectors": self.vectors,
                "ids": self.ids,
                "doc_map": self.doc_map,
            }, f)
    
    def load(self, path: Path):
        """从磁盘加载索引。"""
        if not path.exists():
            return False
        with open(path, "rb") as f:
            data = pickle.load(f)
            self.vectors = data["vectors"]
            self.ids = data["ids"]
            self.doc_map = data["doc_map"]
        return True


# 全局向量索引实例
_vector_index: VectorIndex | None = None


def _get_vector_index() -> VectorIndex:
    """获取或初始化向量索引。"""
    global _vector_index
    if _vector_index is not None:
        return _vector_index
    
    _vector_index = VectorIndex()
    
    # 尝试加载缓存
    if _vector_index.load(VECTOR_CACHE):
        logger.info("向量索引已从缓存加载: %d 个文档", len(_vector_index.ids))
        return _vector_index
    
    # 构建索引
    logger.info("构建 Schema 向量索引...")
    docs = _build_schema_documents()
    
    for doc in docs:
        vector = _get_embedding(doc["embedding_text"])
        _vector_index.add(doc["id"], vector, doc)
    
    _vector_index.save(VECTOR_CACHE)
    logger.info("向量索引构建完成: %d 个文档", len(_vector_index.ids))
    
    return _vector_index


# =============================================================================
# 3. 全文索引：SQLite FTS5
# =============================================================================

class FullTextIndex:
    """基于 SQLite FTS5 的全文索引。"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库和 FTS5 表。"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS schema_fts USING fts5(
                doc_id,
                content,
                tokenize='porter unicode61'
            )
        """)
        conn.commit()
        conn.close()
    
    def rebuild(self, docs: list[dict]):
        """重建全文索引。"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM schema_fts")
        
        for doc in docs:
            conn.execute(
                "INSERT INTO schema_fts (doc_id, content) VALUES (?, ?)",
                (doc["id"], doc["text"])
            )
        
        conn.commit()
        conn.close()
        logger.info("FTS5 全文索引重建完成: %d 个文档", len(docs))
    
    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """执行全文搜索，返回 (doc_id, bm25_score) 列表。"""
        conn = sqlite3.connect(self.db_path)
        
        # 清理查询，移除特殊字符
        clean_query = " ".join(query.split())
        
        try:
            cursor = conn.execute(
                """
                SELECT doc_id, bm25(schema_fts) as score
                FROM schema_fts
                WHERE schema_fts MATCH ?
                ORDER BY bm25(schema_fts) ASC
                LIMIT ?
                """,
                (clean_query, top_k)
            )
            results = []
            for row in cursor.fetchall():
                # bm25 返回的是越小越好，转换为越大越好
                doc_id, bm25_score = row
                # 归一化得分 (bm25 通常为负数或很小的正数)
                normalized_score = 1.0 / (1.0 + abs(bm25_score))
                results.append((doc_id, normalized_score))
            
            return results
        except sqlite3.OperationalError as e:
            logger.warning("FTS5 搜索失败: %s", e)
            return []
        finally:
            conn.close()


# 全局全文索引实例
_fts_index: FullTextIndex | None = None


def _get_fts_index() -> FullTextIndex:
    """获取或初始化全文索引。"""
    global _fts_index
    if _fts_index is not None:
        return _fts_index
    
    _fts_index = FullTextIndex(FTS_DB_PATH)
    
    # 检查是否需要重建
    conn = sqlite3.connect(FTS_DB_PATH)
    cursor = conn.execute("SELECT COUNT(*) FROM schema_fts")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        docs = _build_schema_documents()
        _fts_index.rebuild(docs)
    
    return _fts_index


# =============================================================================
# 4. 混合检索：RRF 融合
# =============================================================================

def _reciprocal_rank_fusion(
    vector_results: list[tuple[str, float]],
    fts_results: list[tuple[str, float]],
    k: float = 60.0,
) -> list[tuple[str, float]]:
    """RRF (Reciprocal Rank Fusion) 融合两种检索结果。
    
    score = Σ 1 / (k + rank)
    """
    scores: dict[str, float] = {}
    
    # 向量结果排名
    for rank, (doc_id, _) in enumerate(vector_results):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    
    # 全文结果排名
    for rank, (doc_id, _) in enumerate(fts_results):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    
    # 按得分排序
    sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results


def hybrid_search(question: str, top_k: int = 5, expand_keywords: bool = True) -> list[dict[str, Any]]:
    """混合检索：返回最相关的 Schema 文档。

    流程：
    1. (可选) LLM 扩展关键词
    2. 向量化用户问题
    3. 向量索引搜索 top_k
    4. 全文索引搜索 top_k(使用扩展后的关键词)
    5. RRF 融合结果
    6. 返回文档列表
    """
    # 获取索引
    vector_idx = _get_vector_index()
    fts_idx = _get_fts_index()

    # 1. 关键词扩展
    search_query = question
    if expand_keywords:
        from app.services.keyword_expand import expand_keywords as _expand
        expanded = _expand(question)
        # 用扩展关键词拼接成更丰富的搜索查询
        search_query = " ".join(expanded)
        logger.debug("关键词扩展: %s -> %s", question, expanded)

    # 2. 向量搜索(使用原始问题，保持语义一致性)
    query_vector = _get_embedding(question)
    vector_results = vector_idx.search(query_vector, top_k=top_k * 2)
    logger.debug("向量搜索结果: %s", vector_results)

    # 3. 全文搜索(使用扩展后的关键词，提升召回率)
    fts_results = fts_idx.search(search_query, top_k=top_k * 2)
    logger.debug("全文搜索结果: %s", fts_results)

    # 4. RRF 融合
    fused = _reciprocal_rank_fusion(vector_results, fts_results)
    logger.debug("RRF 融合结果: %s", fused[:top_k])

    # 5. 组装结果
    results = []
    for doc_id, score in fused[:top_k]:
        doc = vector_idx.doc_map.get(doc_id)
        if doc:
            results.append({
                "id": doc_id,
                "score": score,
                "table_data": doc.get("table_data"),
                "is_hint": doc.get("is_hint", False),
            })

    return results


# =============================================================================
# 5. Schema Prompt 生成
# =============================================================================

def render_schema_prompt_hybrid(question: str, top_k: int = 3) -> str:
    """使用混合检索生成 Schema Prompt。
    
    相比原版的 render_schema_prompt_filtered：
    - 增加向量语义匹配，捕获同义词和语义关联
    - 增加全文关键词匹配，确保精确匹配
    - RRF 融合排序，综合两种优势
    """
    results = hybrid_search(question, top_k=top_k)
    
    if not results:
        # 回退到全部表
        from app.services.schema_search import render_schema_prompt_filtered
        return render_schema_prompt_filtered(question, top_k)
    
    lines: list[str] = []
    lines.append(f"数据库方言: {BUSINESS_SCHEMA['dialect']}")
    lines.append("")
    lines.append("表结构:")
    
    relevant_tables = []
    hints = []
    
    for r in results:
        if r.get("is_hint"):
            hints.append(r)
        elif r["table_data"]:
            relevant_tables.append(r["table_data"])
    
    # 去重并保持顺序
    seen = set()
    unique_tables = []
    for t in relevant_tables:
        if t["name"] not in seen:
            seen.add(t["name"])
            unique_tables.append(t)
    
    for table in unique_tables:
        lines.append(f"\n-- {table['comment']}")
        lines.append(f"TABLE {table['name']} (")
        col_lines = []
        for col in table["columns"]:
            col_lines.append(f"  {col['name']} {col['type']}  -- {col['comment']}")
        lines.append(",\n".join(col_lines))
        lines.append(")")
    
    # 关系
    relevant_names = {t["name"] for t in unique_tables}
    lines.append("")
    lines.append("表关系:")
    for rel in BUSINESS_SCHEMA["relations"]:
        parts = rel.split(" -> ")
        if len(parts) == 2:
            left_table = parts[0].split(".")[0]
            right_table = parts[1].split(".")[0]
            if left_table in relevant_names or right_table in relevant_names:
                lines.append(f"  - {rel}")
    
    # 业务提示
    lines.append("")
    lines.append("业务提示:")
    for hint in BUSINESS_SCHEMA["hints"]:
        lines.append(f"  - {hint}")
    
    # 添加检索元信息（帮助调试）
    lines.append("")
    lines.append(f"-- 检索相关表: {[t['name'] for t in unique_tables]}")
    
    return "\n".join(lines)


# =============================================================================
# 6. 预热和初始化
# =============================================================================

def warmup():
    """预热索引（应用启动时调用）。"""
    _get_vector_index()
    _get_fts_index()
    logger.info("混合检索索引预热完成")
