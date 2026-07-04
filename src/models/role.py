"""Role and Permission models (src/ plane mirror).

The canonical models live in :mod:`app.models.role`. This module
re-exports them so that the Alembic env wiring and CLI scripts can
discover them without depending on the FastAPI request plane.
"""

from app.models.role import Permission, Role, RolePermissions

__all__ = ["Permission", "Role", "RolePermissions"]
