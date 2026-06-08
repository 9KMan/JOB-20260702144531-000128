"""Application configuration loaded from environment variables.

All secrets and environment-specific values flow through this module so that
no production secret is ever hardcoded in source.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised settings sourced from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    PROJECT_NAME: str = "Tuinui Looker Studio Backend"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])

    # GCP
    GCP_PROJECT_ID: str = "tuinui-analytics"
    GCP_BIGQUERY_DATASET: str = "looker_studio_metrics"
    GCP_BIGQUERY_LOCATION: str = "US"
    GCP_STORAGE_BUCKET: str = "tuinui-looker-exports"
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://tuinui:tuinui@localhost:5432/tuinui"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://tuinui:tuinui@localhost:5432/tuinui"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Airflow
    AIRFLOW_HOME: str = "/opt/airflow"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Looker Studio
    LOOKER_STUDIO_REFRESH_INTERVAL_MINUTES: int = 15
    ENABLE_DASHBOARD_CACHE: bool = True
    DASHBOARD_CACHE_TTL_SECONDS: int = 900

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Feature flags
    ENABLE_BIGQUERY_SYNC: bool = True
    ENABLE_WEBHOOKS: bool = True
    ENABLE_AIRFLOW_DAGS: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        return v.upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
