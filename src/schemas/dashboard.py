"""Dashboard Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DashboardBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    looker_url: Optional[str] = Field(default=None, max_length=1024)
    config_json: Dict[str, Any] = Field(default_factory=dict)
    refresh_interval_minutes: int = Field(default=15, ge=1, le=1440)
    is_published: bool = False

    @field_validator("slug")
    @classmethod
    def _slug_charset(cls, v: str) -> str:
        v = v.strip().lower()
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("slug must be lowercase alphanumeric, '-' or '_'")
        return v


class DashboardCreate(DashboardBase):
    dataset_id: uuid.UUID


class DashboardUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    looker_url: Optional[str] = Field(default=None, max_length=1024)
    config_json: Optional[Dict[str, Any]] = None
    refresh_interval_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    is_published: Optional[bool] = None
    dataset_id: Optional[uuid.UUID] = None


class DashboardRead(DashboardBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    owner_id: Optional[uuid.UUID] = None
    view_count: int
    created_at: datetime
    updated_at: datetime
