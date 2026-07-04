"""Audit log model (src/ plane mirror).

The canonical model lives in :mod:`app.models.audit_log`. This module
re-exports it so that the Alembic env wiring and CLI scripts can
discover it without depending on the FastAPI request plane.
"""

from app.models.audit_log import AuditLog

__all__ = ["AuditLog"]
