import jieba.analyse

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def extract_keywords(state: DataAgentState, runtime):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "抽取关键字", "status": "running"})

    query = state["query"]

    allow_pos = (
        "n", "nr", "ns", "nt", "nz", "v", "vn", "a", "an", "eng", "i", "l"
    )

    keywords = jieba.analyse.extract_tags(query, allowPOS=allow_pos)
    keywords = list(set(keywords + [query]))

    writer({"type": "progress", "step": "抽取关键字", "status": "success"})
    return {"keywords": keywords}
