"""Pydantic request/response models for the ingestion API."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Metadata(BaseModel):
    """Optional metadata associated with an ingested record."""

    url: Optional[str] = Field(None, description="Source URL if applicable")
    collected_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp — defaults to server receipt time if omitted",
    )
    tags: Optional[List[str]] = Field(default_factory=list, description="User-provided tags")
    extra: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional arbitrary metadata",
    )


class IngestRequest(BaseModel):
    """
    Request payload for the /ingest endpoint.

    Attributes:
        source: Origin type — one of 'api', 'webhook', 'scraper'.
        content: Raw text or HTML content to process.
        metadata: Optional metadata dictionary.
    """

    source: str = Field(
        ...,
        description="Data origin: 'api', 'webhook', or 'scraper'",
        examples=["api"],
    )
    content: str = Field(
        ...,
        description="Raw text or HTML content to be processed by the ETL pipeline",
        min_length=1,
        examples=["<html>...</html>"],
    )
    metadata: Optional[Metadata] = Field(
        default=None,
        description="Optional metadata: URL, collected_at timestamp, tags, extra fields",
    )

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v not in ("api", "webhook", "scraper"):
            raise ValueError(f"source must be one of: api, webhook, scraper — got '{v}'")
        return v


class IngestResponse(BaseModel):
    """
    Response payload after a record has been accepted for processing.

    Attributes:
        status: Always 'accepted' on success.
        record_id: UUID assigned to this record for tracking.
        queued_at: ISO 8601 timestamp when the record was queued.
    """

    status: str = Field("accepted", description="Processing status")
    record_id: str = Field(..., description="UUID assigned to this record")
    queued_at: str = Field(..., description="ISO 8601 timestamp of queue admission")


class WebhookPayload(BaseModel):
    """
    Simplified webhook payload for the /webhook/ingest endpoint.

    Attributes:
        data: The raw content string received via webhook.
        metadata: Optional metadata fields.
    """

    data: str = Field(..., description="Raw content received via webhook", min_length=1)
    metadata: Optional[Metadata] = Field(default_factory=Metadata)

    @field_validator("data")
    @classmethod
    def validate_data(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("webhook 'data' field cannot be empty")
        return v


class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: str = Field(..., description="Human-readable error message")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")