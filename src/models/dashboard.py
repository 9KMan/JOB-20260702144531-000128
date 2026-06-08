"""Dashboard ORM model representing a Looker Studio report configuration."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base

if TYPE_CHECKING:
    from src.models.dataset import Dataset


class Dashboard(Base):
    """A Looker Studio dashboard bound to a registered BigQuery dataset."""

    __tablename__ = "dashboards"
    __table_args__ = (
        {"comment": "Looker Studio dashboard definitions and configuration."},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    looker_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    refresh_interval_minutes: Mapped[int] = mapped_column(default=15, nullable=False)
    is_published: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    view_count: Mapped[int] = mapped_column(default=0, nullable=False)

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
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
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="dashboards")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Dashboard {self.title} slug={self.slug}>"
