"""Metric Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class MetricBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    label: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    sql_expression: str = Field(..., min_length=1)
    aggregation: str = Field(default="SUM", max_length=64)
    unit: Optional[str] = Field(default=None, max_length=32)
    format_pattern: Optional[str] = Field(default=None, max_length=64)
    meta_json: Dict[str, Any] = Field(default_factory=dict)


class MetricCreate(MetricBase):
    dataset_id: uuid.UUID


class MetricUpdate(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    sql_expression: Optional[str] = Field(default=None, min_length=1)
    aggregation: Optional[str] = Field(default=None, max_length=64)
    unit: Optional[str] = Field(default=None, max_length=32)
    format_pattern: Optional[str] = Field(default=None, max_length=64)
    meta_json: Optional[Dict[str, Any]] = None


class MetricRead(MetricBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    last_value: Optional[float] = None
    last_calculated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
