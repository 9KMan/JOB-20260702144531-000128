"""SQLAlchemy declarative base for the ``app/`` plane.

This is a separate ``Base`` from :class:`src.models.base.Base`, but
both classes bind to the same physical metadata registry at runtime
because the engine is shared. Keeping two ``Base`` classes lets the
``src/`` and ``app/`` planes import independently without circular
dependencies — Alembic uses ``src.models.base.Base.metadata`` while
FastAPI routes use ``app.models.base.Base.metadata``.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for ``app/``-plane ORM models."""

    pass