"""LangGraph Agent 工作流。

将 NL2SQL 流程拆分为可编排的节点图：
extract_keywords -> hybrid_search -> generate_sql -> validate_sql -> [correct_sql] -> execute_sql -> summarize
"""
