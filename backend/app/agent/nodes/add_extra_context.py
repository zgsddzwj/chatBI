from datetime import datetime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, DateInfoState


async def add_extra_context(state: DataAgentState, runtime):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "添加额外上下文信息", "status": "running"})

    dw_mysql_repository = runtime.context["dw_mysql_repository"]

    try:
        today = datetime.today()
        date = today.strftime("%Y-%m-%d")
        weekday = today.strftime("%A")
        quarter = f"Q{(today.month - 1) // 3 + 1}"

        date_info = DateInfoState(date=date, weekday=weekday, quarter=quarter)
        db_info = await dw_mysql_repository.get_db_info()

        writer({"type": "progress", "step": "添加额外上下文信息", "status": "success"})
        return {"date_info": date_info, "db_info": db_info}
    except Exception as e:
        writer({"type": "progress", "step": "添加额外上下文信息", "status": "error"})
        raise
