"""Dataset Pydantic schemas (request/response)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DatasetBase(BaseModel):
    """Common dataset attributes."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    bigquery_project: str = Field(..., min_length=3, max_length=255)
    bigquery_dataset: str = Field(..., min_length=1, max_length=255)
    table_name: str = Field(..., min_length=1, max_length=255)
    schema_json: Dict[str, Any] = Field(default_factory=dict)
    refresh_interval_minutes: int = Field(default=15, ge=1, le=1440)
    is_active: bool = True

    @field_validator("bigquery_project", "bigquery_dataset", "table_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v


class DatasetCreate(DatasetBase):
    """Payload for creating a new dataset."""


class DatasetUpdate(BaseModel):
    """Partial update — every field optional."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    bigquery_project: Optional[str] = Field(default=None, min_length=3, max_length=255)
    bigquery_dataset: Optional[str] = Field(default=None, min_length=1, max_length=255)
    table_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    schema_json: Optional[Dict[str, Any]] = None
    refresh_interval_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    is_active: Optional[bool] = None


class DatasetRead(DatasetBase):
    """Read-side dataset response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
