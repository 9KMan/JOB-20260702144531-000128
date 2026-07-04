"""User and UserRole models (src/ plane mirror).

The canonical model lives in :mod:`app.models.user`. This is a thin
re-export so CLI tools and migrations can operate without depending
on the FastAPI request plane.
"""

from app.models.user import User, UserRoleEnum

__all__ = ["User", "UserRoleEnum"]
