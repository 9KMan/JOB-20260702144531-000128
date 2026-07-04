"""Database models package for the ``src/`` plane (legacy + CLI tools).

The authoritative application-layer models live in ``app.models``. The
duplication here is intentional: ``src/`` is the *migrations* plane
(Alembic uses ``src.models.base.Base.metadata`` to autogenerate
revisions), while ``app/`` is the request/response plane (FastAPI
endpoints work with ``app.models``).

Both planes import the same physical tables — declared against
distinct ``Base`` subclasses that resolve to the same set of records.
Alembic env.py imports from ``app.models.base.Base`` to keep a
single source of truth.
"""

from src.models.base import Base, TimestampMixin

__all__ = ["Base", "TimestampMixin"]
