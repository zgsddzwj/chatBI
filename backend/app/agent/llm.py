from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config

# 延迟初始化，避免在导入时就触发 API 调用
_llm = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = init_chat_model(
            model=app_config.llm.model_name,
            model_provider="openai",
            api_key=app_config.llm.api_key or "missing",
            base_url=app_config.llm.base_url,
            temperature=0,
        )
    return _llm


# 兼容旧代码直接引用 llm 的写法
class _LLMProxy:
    def __getattr__(self, name):
        return getattr(get_llm(), name)


llm = _LLMProxy()
