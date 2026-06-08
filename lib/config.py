"""Environment variable config loader."""
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    GCP_PROJECT_ID: str = Field(default='')
    GCP_BIGQUERY_DATASET: str = Field(default='looker_pipeline')
    GCP_BIGQUERY_TABLE: str = Field(default='raw_data')
    GCP_SERVICE_ACCOUNT_KEY: Path = Field(default=Path('./gcp-key.json'))
    GCS_BUCKET: str = Field(default='')
    AIRFLOW_HOME: Path = Field(default=Path('./airflow'))
    API_PORT: int = Field(default=8080)
    LOG_LEVEL: str = Field(default='INFO')
    AI_TAGGER_MODEL: str = Field(default='sentence-transformers/all-MiniLM-L6-v2')

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore'


settings = Settings()
