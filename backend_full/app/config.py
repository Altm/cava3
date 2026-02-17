from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "Cavina Backoffice"
    env: str = Field("DEV", description="Environment name for toggling features")
    database_url: str = Field("sqlite:///:memory:", env="DATABASE_URL")
    jwt_secret_key: str = Field("change-me", env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    swagger_enabled: bool = Field(True, env="SWAGGER_ENABLED")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    structlog_json: bool = Field(True, env="STRUCTLOG_JSON")
    hmac_clock_skew_seconds: int = 30
    default_currency: str = "EUR"
    sales_terminal_id: str = Field("T-1", env="SALES_TERMINAL_ID")
    sales_self_base_url: str = Field("http://127.0.0.1:8000", env="SALES_SELF_BASE_URL")
    sales_self_timeout_seconds: int = Field(10, env="SALES_SELF_TIMEOUT_SECONDS")
    sales_event_default_status: str = Field("pending", env="SALES_EVENT_DEFAULT_STATUS")
    sales_allow_aggregate_fallback_for_serial: bool = Field(
        True,
        env="SALES_ALLOW_AGGREGATE_FALLBACK_FOR_SERIAL",
    )
    glasses_per_bottle: int = 5
    loaf_fraction: str = "0.1"
    jar_fraction: str = "0.1"
    admin_username: str = Field("admin", env="ADMIN_USERNAME")
    admin_password: str = Field("admin", env="ADMIN_PASSWORD")
    default_location_id: int = Field(1, env="DEFAULT_LOCATION_ID")
    default_location_name: str = Field("Main Warehouse", env="DEFAULT_LOCATION_NAME")

    class Config:
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def super_admin_ids(self) -> set:
        import os
        ids_str = os.getenv("SUPER_ADMIN_IDS", "")
        if ids_str:
            return {int(x.strip()) for x in ids_str.split(",") if x.strip()}
        return set()


@lru_cache()
def get_settings() -> Settings:
    return Settings()
