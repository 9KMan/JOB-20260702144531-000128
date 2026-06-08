"""Metric ORM model — individual KPIs derived from BigQuery for Looker Studio."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base

if TYPE_CHECKING:
    from src.models.dataset import Dataset


class Metric(Base):
    """A single named metric tied to a dataset with a BigQuery SQL definition."""

    __tablename__ = "metrics"
    __table_args__ = (
        {"comment": "Metrics computed from BigQuery and surfaced in dashboards."},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sql_expression: Mapped[str] = mapped_column(Text, nullable=False)
    aggregation: Mapped[str] = mapped_column(String(64), nullable=False, default="SUM")
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    format_pattern: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_calculated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    meta_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="metrics")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Metric {self.name} value={self.last_value}>"
