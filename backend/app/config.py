import logging
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="local", description="local / docker / production")

    log_level: str = Field(default="INFO")

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # Embedding 配置（支持独立配置，默认复用 deepseek）
    embedding_api_key: str = Field(default="", description="Embedding API Key，为空则复用 deepseek_api_key")
    embedding_base_url: str = Field(default="", description="Embedding Base URL，为空则复用 deepseek_base_url")
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding 模型名称")

    business_db_url: str = "sqlite:///./data/business.db"
    business_db_readonly: bool = Field(default=False)
    app_db_url: str = "sqlite:///./data/app.db"

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    sql_row_limit: int = Field(default=1000, ge=1, le=50_000)
    llm_timeout_seconds: int = Field(default=60, ge=5, le=600)
    sql_query_timeout_seconds: int = Field(default=30, ge=1, le=300)

    jwt_secret: str = Field(default="", description="JWT 签名密钥，生产环境必填")
    admin_password: str = Field(default="", description="默认管理员密码，生产环境必填")
    allow_public_register: bool = Field(default=True)
    rate_limit_requests: int = Field(default=30, ge=1, le=1000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    cache_ttl_seconds: int = Field(default=300, ge=0, le=86400)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @field_validator("log_level")
    @classmethod
    def log_level_must_be_known(cls, v: str) -> str:
        upper = v.upper()
        if upper not in logging._nameToLevel:  # noqa: SLF001
            raise ValueError(f"无效的 log_level: {v}")
        return upper

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
