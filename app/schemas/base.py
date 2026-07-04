"""Common Pydantic mix-ins used across the API surface.

Centralising these here avoids subtle drift between endpoints —
e.g., timestamps should always be serialised the same way.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base model for API request/response payloads."""
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        json_schema_extra={"examples": []},
    )


class TimestampedModel(ApiModel):
    """Mixin for payloads that include creation / update timestamps."""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None


def utc_now() -> datetime:
    """Return the current UTC time as a tz-aware datetime."""
    return datetime.now(timezone.utc)