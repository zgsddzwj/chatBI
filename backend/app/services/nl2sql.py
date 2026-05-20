"""NL2SQL 核心服务：自然语言 -> SQL -> 执行 -> 总结。"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from app.config import get_settings
from app.database import business_engine
from app.schema_meta import render_schema_prompt
from app.services.schema_search import render_schema_prompt_filtered
from app.services.cache import get_cached, set_cache
from app.services.chart import recommend_chart
from app.services.llm import get_llm
from app.services.sql_safety import UnsafeSQLError, ensure_limit, validate_sql
from app.services.sql_fixer import try_fix_sql

logger = logging.getLogger(__name__)


SQL_SYSTEM_PROMPT = """你是一位资深的数据分析师，擅长将业务问题翻译成 SQL。

请严格遵守以下规则：
1. 只生成 **SELECT** 查询，禁止任何写操作。
2. 使用提供的表结构和字段，不要臆造表名或字段名。
3. 使用 SQLite 语法（如日期处理用 strftime）。
4. 若需要按时间聚合，列名请使用易读别名，例如 month、year、date。
5. 若问题涉及"销售额/营收/GMV"，使用 SUM(orders.amount)。
6. 若问题涉及"已完成订单"或"有效订单"，加上 status IN ('paid','shipped','completed')。
7. 输出必须是 **严格的 JSON 对象**，结构为：
   {
     "sql": "...",                 // 生成的 SQL（单条 SELECT）
     "explanation": "...",          // 一句话解释 SQL 的含义
     "needs_clarification": false,  // 若问题模糊无法生成 SQL，则为 true
     "clarification": ""            // 当 needs_clarification=true 时的追问
   }
8. SQL 中不要带分号结尾。
9. 默认按合理的维度排序（例如时间升序、金额降序）。
"""


SUMMARY_SYSTEM_PROMPT = """你是一位数据分析助手。根据用户的问题、执行的 SQL 和查询结果，
用简洁的中文回答用户（2-4 句话），突出关键数字、趋势或对比。
不要重复展示完整数据，不要写代码块。"""


class NL2SQLError(Exception):
    pass


class NL2SQLService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._llm = get_llm()

    def recommend_chart(self, columns: list[str], rows: list[list[Any]]) -> dict[str, Any]:
        """暴露图表推荐方法，供流式接口调用。"""
        return recommend_chart(columns, rows)

    def _build_user_prompt(self, question: str, history: list[dict[str, str]] | None) -> str:
        parts: list[str] = []
        parts.append("# 数据库 Schema\n")
        # 使用智能检索过滤相关表
        parts.append(render_schema_prompt_filtered(question, top_k=3))
        if history:
            parts.append("\n# 最近的对话（用于理解上下文）")
            for h in history[-6:]:
                parts.append(f"{h['role']}: {h['content']}")
        parts.append("\n# 当前问题")
        parts.append(question)
        parts.append("\n请输出 JSON。")
        return "\n".join(parts)

    def generate_sql(self, question: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
        prompt = self._build_user_prompt(question, history)
        try:
            result = self._llm.chat_json(SQL_SYSTEM_PROMPT, prompt, temperature=0.0)
        except ValueError as exc:
            raise NL2SQLError(str(exc)) from exc
        if not isinstance(result, dict):
            raise NL2SQLError("模型返回格式异常，无法解析为 JSON 对象")
        if result.get("needs_clarification"):
            return {
                "needs_clarification": True,
                "clarification": result.get("clarification") or "你的问题信息不够，能否补充？",
            }
        sql = (result.get("sql") or "").strip()
        if not sql:
            raise NL2SQLError("模型未返回 SQL")
        validated = validate_sql(sql)
        limited = ensure_limit(validated, self._settings.sql_row_limit)
        return {
            "needs_clarification": False,
            "sql": limited,
            "explanation": result.get("explanation", ""),
        }

    def execute_sql(self, sql: str, question: str | None = None, max_retries: int = 2) -> dict[str, Any]:
        """执行 SQL，失败时尝试自动纠错重试。"""
        # 先查缓存
        cached = get_cached(sql)
        if cached:
            logger.info("SQL 缓存命中: %s", sql[:80])
            return cached

        last_error: str | None = None
        current_sql = sql

        for attempt in range(max_retries + 1):
            try:
                with business_engine.connect() as conn:
                    cursor = conn.execute(text(current_sql))
                    columns = list(cursor.keys())
                    rows = [list(r) for r in cursor.fetchall()]
                result = {"columns": columns, "rows": rows, "row_count": len(rows)}
                # 如果经过修正，返回修正后的 SQL
                if attempt > 0:
                    result["fixed_sql"] = current_sql
                return result
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                logger.warning("SQL 执行失败 (attempt %d/%d): %s", attempt + 1, max_retries + 1, last_error[:200])

                # 最后一次尝试，不再纠错
                if attempt >= max_retries or not question:
                    break

                # 尝试纠错
                schema_prompt = render_schema_prompt_filtered(question, top_k=3)
                fix_result = try_fix_sql(question, current_sql, last_error, schema_prompt, self._settings.sql_row_limit)
                if fix_result and not fix_result.get("needs_clarification"):
                    current_sql = fix_result["sql"]
                    logger.info("SQL 已修正: %s", current_sql[:100])
                else:
                    # 无法修正，直接抛出原错误
                    break

        raise NL2SQLError(f"SQL 执行失败: {last_error}")

    def summarize(self, question: str, sql: str, data: dict[str, Any]) -> str:
        preview_rows = data["rows"][:20]
        user_msg = (
            f"用户问题: {question}\n\n"
            f"执行 SQL:\n{sql}\n\n"
            f"查询结果 (前 {len(preview_rows)} 行, 共 {data['row_count']} 行):\n"
            f"列: {data['columns']}\n"
            f"数据: {preview_rows}\n\n"
            "请用 2-4 句中文总结关键洞察。"
        )
        try:
            return self._llm.chat_text(SUMMARY_SYSTEM_PROMPT, user_msg, temperature=0.3)
        except Exception:
            logger.exception("总结失败，使用兜底文案")
            return f"查询完成，共返回 {data['row_count']} 行结果。"

    def ask(self, question: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
        """完整流程：问题 -> SQL -> 执行 -> 图表 -> 总结。"""
        try:
            sql_result = self.generate_sql(question, history)
        except UnsafeSQLError as exc:
            raise NL2SQLError(f"生成的 SQL 不安全: {exc}") from exc

        if sql_result.get("needs_clarification"):
            return {
                "type": "clarification",
                "clarification": sql_result["clarification"],
            }

        sql = sql_result["sql"]
        data = self.execute_sql(sql, question=question)
        # 如果 SQL 被修正，使用修正后的版本
        fixed_sql = data.pop("fixed_sql", None)
        if fixed_sql:
            sql = fixed_sql
        chart = recommend_chart(data["columns"], data["rows"])

        # 缓存结果
        set_cache(sql, data, chart)
        if data["row_count"] > 0:
            summary = (self.summarize(question, sql, data) or "").strip()
            if not summary:
                summary = f"查询完成，共返回 {data['row_count']} 行结果。"
        else:
            summary = "未查询到匹配数据。"

        return {
            "type": "answer",
            "sql": sql,
            "explanation": sql_result.get("explanation", ""),
            "data": data,
            "chart": chart,
            "summary": summary,
        }


_singleton: NL2SQLService | None = None


def get_nl2sql_service() -> NL2SQLService:
    global _singleton
    if _singleton is None:
        _singleton = NL2SQLService()
    return _singleton
