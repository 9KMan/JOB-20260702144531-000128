"""Canonical User model for the ``app/`` plane.

A ``User`` row represents one person (or service account) that can
authenticate against the platform. Identity comes from SSO when
available (``sso_provider`` + ``sso_subject``); local fallback uses
``password_hash``.
"""

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class UserRoleEnum(str, enum.Enum):
    """Coarse-grained role enum, used for fast permission checks."""
    ADMIN = "admin"
    REVIEWER = "reviewer"
    OPERATOR = "operator"
    VIEWER = "viewer"


# M:N junction between users and roles — declared as the
# ``user_roles`` Table. The User class's ``user_roles`` collection
# maps the same physical table.


class User(Base):
    """A user account."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # SSO identity (mutually exclusive with local password)
    sso_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sso_subject: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Local fallback
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Role enum (fast check) + M:N roles table (granular)
    primary_role: Mapped[UserRoleEnum] = mapped_column(
        Enum(UserRoleEnum, name="user_role_enum"),
        nullable=False,
        default=UserRoleEnum.VIEWER,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"