"""Canonical RBAC models for the ``app/`` plane.

Three tables:
  - ``permissions``      — global catalog of permission codes.
  - ``roles``            — named roles; each may carry many permissions.
  - ``role_permissions`` — M:N junction between roles and permissions.

Users gain a role via the separate ``user_roles`` M:N table
(declared in :mod:`src.models.user`). This module deliberately
focuses on the role ↔ permission side of the relationship.
"""

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


# M:N junction between roles and permissions — declared as the
# ``role_permissions`` Table. The ``RolePermissions`` ORM class below
# maps the same physical table.


class Permission(Base):
    """A single permission code, e.g. ``task:create``."""

    __tablename__ = "permissions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<Permission {self.code}>"


class Role(Base):
    """A named role; carries many permissions via ``role_permissions``."""

    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    permissions: Mapped[list["RolePermissions"]] = relationship(
        "RolePermissions",
        back_populates="role",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class RolePermissions(Base):
    """Junction row between a role and a permission."""

    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped["Role"] = relationship("Role", back_populates="permissions")
    permission: Mapped["Permission"] = relationship("Permission")