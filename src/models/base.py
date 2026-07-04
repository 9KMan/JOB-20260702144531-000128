"""SQLAlchemy base configuration and mixins for the src/ plane.

The authoritative base lives in :mod:`app.models.base` (with the
proper ``UUIDMixin`` and a single declarative class). This module
exists so that the Alembic env wiring and CLI tools have a stable
import path that does NOT pull in FastAPI dependencies.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models in the ``src/`` plane.

    :class:`app.models.base.Base` is the same metadata registry under
    a different name; both share the same physical tables because the
    runtime binds a single engine to both.
    """

    pass


class TimestampMixin:
    """Mixin that adds ``created_at`` and ``updated_at`` timestamps."""

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
