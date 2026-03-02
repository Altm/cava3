from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "Cavina Backoffice"
    env: str = Field("DEV", description="Environment name for toggling features")
    database_url: str = Field("sqlite:///:memory:", env="DATABASE_URL")
    jwt_secret_key: Optional[str] = Field(None, env="JWT_SECRET_KEY")
    jwt_secret_keys: Optional[str] = Field(None, env="JWT_SECRET_KEYS")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    swagger_enabled: bool = Field(True, env="SWAGGER_ENABLED")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    structlog_json: bool = Field(True, env="STRUCTLOG_JSON")
    hmac_clock_skew_seconds: int = 30
    default_currency: str = "EUR"
    sales_terminal_id: str = Field("T-1", env="SALES_TERMINAL_ID")
    sales_terminal_user_id: Optional[int] = Field(None, env="SALES_TERMINAL_USER_ID")
    sales_self_base_url: str = Field("http://127.0.0.1:8000", env="SALES_SELF_BASE_URL")
    sales_self_timeout_seconds: int = Field(10, env="SALES_SELF_TIMEOUT_SECONDS")
    sales_event_default_status: str = Field("pending", env="SALES_EVENT_DEFAULT_STATUS")
    sales_allow_aggregate_fallback_for_serial: bool = Field(
        True,
        env="SALES_ALLOW_AGGREGATE_FALLBACK_FOR_SERIAL",
    )
    admin_username: str = Field("admin", env="ADMIN_USERNAME")
    admin_password: Optional[str] = Field(None, env="ADMIN_PASSWORD")
    bootstrap_default_admin: bool = Field(False, env="BOOTSTRAP_DEFAULT_ADMIN")
    image_upload_max_bytes: int = Field(5 * 1024 * 1024, env="IMAGE_UPLOAD_MAX_BYTES")
    rate_limit_enabled: bool = Field(True, env="RATE_LIMIT_ENABLED")
    rate_limit_default_per_hour: int = Field(500, env="RATE_LIMIT_DEFAULT_PER_HOUR")
    rate_limit_auth_per_hour: int = Field(60, env="RATE_LIMIT_AUTH_PER_HOUR")
    rate_limit_sales_per_hour: int = Field(300, env="RATE_LIMIT_SALES_PER_HOUR")
    rate_limit_window_seconds: int = Field(3600, env="RATE_LIMIT_WINDOW_SECONDS")
    rate_limit_trust_x_forwarded_for: bool = Field(False, env="RATE_LIMIT_TRUST_X_FORWARDED_FOR")
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

    @property
    def jwt_verification_keys(self) -> list[str]:
        values: list[str] = []
        if self.jwt_secret_keys:
            values.extend([item.strip() for item in self.jwt_secret_keys.split(",") if item.strip()])
        if self.jwt_secret_key:
            values.append(self.jwt_secret_key.strip())
        deduplicated = list(dict.fromkeys([value for value in values if value]))
        if deduplicated:
            return deduplicated
        return ["change-me"]

    @property
    def jwt_signing_key(self) -> str:
        return self.jwt_verification_keys[0]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
