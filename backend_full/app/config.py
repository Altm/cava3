from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "Cavina Inventory"
    environment: str = Field("development", description="Environment name for toggling features")
    database_url: str = Field(..., env="DATABASE_URL")
    jwt_secret_key: str = Field("change-me", env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    swagger_enabled: bool = Field(True, env="SWAGGER_ENABLED")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    structlog_json: bool = Field(True, env="STRUCTLOG_JSON")
    hmac_clock_skew_seconds: int = 300
    default_currency: str = "USD"
    glasses_per_bottle: int = 5
    loaf_fraction: str = "0.1"
    jar_fraction: str = "0.1"
    admin_username: str = Field("admin", env="ADMIN_USERNAME")
    admin_password: str = Field("admin", env="ADMIN_PASSWORD")

    class Config:
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
