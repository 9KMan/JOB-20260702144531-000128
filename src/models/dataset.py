"""Dataset ORM model representing a BigQuery source powering a Looker Studio report."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base

if TYPE_CHECKING:
    from src.models.dashboard import Dashboard
    from src.models.metric import Metric


class Dataset(Base):
    """A BigQuery dataset registered for use by Looker Studio dashboards."""

    __tablename__ = "datasets"
    __table_args__ = (
        {"comment": "Registered BigQuery datasets that back Looker Studio reports."},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    bigquery_project: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    bigquery_dataset: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    refresh_interval_minutes: Mapped[int] = mapped_column(default=15, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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

    dashboards: Mapped[List["Dashboard"]] = relationship(
        "Dashboard",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
    metrics: Mapped[List["Metric"]] = relationship(
        "Metric",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Dataset {self.name} project={self.bigquery_project}>"
