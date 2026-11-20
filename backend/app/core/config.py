"""Application settings, read from environment variables (and a .env file in dev)."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "postgresql+psycopg://adaptaid:adaptaid@localhost:5434/adaptaid"

    # Auth
    jwt_secret: str = "dev-only-change-me-please-0123456789abcdef"
    jwt_expire_hours: int = 24 * 7
    cookie_name: str = "adaptaid_session"
    cookie_secure: bool = False
    teacher_invite_code: str = "TEACH-2026"

    # Jobs
    scheduler_enabled: bool = False
    job_hour: int = 2

    # Testing aid: extra routes used only by the proxy contract test
    enable_contract_routes: bool = False

    display_tz: str = "Asia/Kolkata"


@lru_cache
def get_settings() -> Settings:
    return Settings()
