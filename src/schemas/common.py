"""Shared Pydantic primitives (pagination, health, error envelopes)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str
    timestamp: datetime
    dependencies: Dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
    request_id: Optional[uuid.UUID] = None
    extras: Dict[str, Any] = Field(default_factory=dict)


class Page(BaseModel, Generic[T]):
    """Generic pagination wrapper."""

    items: List[T]
    total: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    has_next: bool = False
