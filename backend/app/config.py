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

    business_db_url: str = "sqlite:///./data/business.db"
    app_db_url: str = "sqlite:///./data/app.db"

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    sql_row_limit: int = Field(default=1000, ge=1, le=50_000)
    llm_timeout_seconds: int = Field(default=60, ge=5, le=600)

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
