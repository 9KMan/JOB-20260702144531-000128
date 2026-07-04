"""Canonical IngestedRow model for the ``app/`` plane.

An ``IngestedRow`` represents one row that has been pulled from an
external source and normalised for downstream processing. The
``source_row_hash`` column is the idempotency key — two rows with
the same hash under the same ``source_id`` are treated as duplicates.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class IngestedRow(Base):
    """One normalised row of ingested data."""

    __tablename__ = "ingested_rows"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_row_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    ingested_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        # Idempotency: at most one row per (source_id, source_row_hash).
        {"sqlite_autoincrement": False},
    )