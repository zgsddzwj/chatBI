from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def execute_sql(state: DataAgentState, runtime):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "执行SQL", "status": "running"})

    sql = state["sql"]
    dw_mysql_repository = runtime.context["dw_mysql_repository"]

    try:
        result = await dw_mysql_repository.execute_sql(sql)
        writer({"type": "progress", "step": "执行SQL", "status": "success"})
        writer({"type": "result", "data": result})
    except Exception as e:
        writer({"type": "progress", "step": "执行SQL", "status": "error"})
        raise
