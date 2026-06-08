"""Pydantic request/response models for the ingest API."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IngestRecord(BaseModel):
    id: str = Field(default='', description='UUID primary key')
    source: str = Field(description='One of: api, webhook, scraper')
    content: str = Field(description='Raw text content')
    title: Optional[str] = Field(default=None, description='Optional title')
    url: Optional[str] = Field(default=None, description='Origin URL if applicable')
    tags: Optional[str] = Field(default='', description='Comma-separated AI-generated tags')
    ingested_at: Optional[datetime] = Field(default=None, description='When record entered the pipeline')
    processed_at: Optional[datetime] = Field(default=None, description='When ETL/AI tagging completed')
    dag_run_id: Optional[str] = Field(default='', description='Airflow DAG run identifier')

    class Config:
        json_schema_extra = {
            'example': {
                'source': 'api',
                'content': 'Quarterly earnings report highlights15% revenue growth',
                'title': 'Q3 Earnings Summary',
                'url': 'https://example.com/earnings/q3',
            }
        }


class IngestResponse(BaseModel):
    id: str
    blob_name: str
    status: str


class BatchIngestRequest(BaseModel):
    records: list[IngestRecord] = Field(min_length=1, max_length=1000)


class WebhookPayload(BaseModel):
    event: str = Field(description='Event type, e.g. push, pull_request')
    repository: Optional[str] = Field(default=None, description='Repository name or URL')
    content: Optional[str] = Field(default=None, description='Webhook payload content')
