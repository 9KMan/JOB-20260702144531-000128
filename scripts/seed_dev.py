#!/usr/bin/env python3
"""Seed a development user + permissions for local testing.

Usage:
    python3 -m scripts.seed_dev

Idempotent — safe to re-run; existing rows are left in place.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from src.config import get_settings
from src.database import async_session_factory, init_db
from src.models.role import Permission, Role, RolePermissions
from src.models.user import User, UserRoleEnum


SEED_PERMISSIONS = [
    ("task:create", "Create new tasks"),
    ("task:cancel", "Cancel pending or running tasks"),
    ("review:suggestion", "Approve / reject suggestions"),
    ("audit:read", "Read the audit log"),
    ("user:manage", "Manage users and roles"),
    ("template:edit", "Create / edit templates"),
]

SEED_ROLES = {
    "admin": [p[0] for p in SEED_PERMISSIONS],
    "reviewer": ["review:suggestion", "audit:read"],
    "operator": ["task:create", "task:cancel", "audit:read"],
    "viewer": ["audit:read"],
}

SEED_USERS = [
    {
        "email": "dev@local",
        "full_name": "Dev User",
        "primary_role": UserRoleEnum.ADMIN,
        "password_hash": None,
    },
]


async def seed() -> None:
    """Insert seed rows if absent."""
    settings = get_settings()
    if not settings.is_development:
        print("Refusing to seed — not in development mode.")
        return

    await init_db()
    async with async_session_factory() as session:
        # Permissions
        perm_by_code: dict[str, Permission] = {}
        for code, desc in SEED_PERMISSIONS:
            existing = (
                await session.execute(
                    select(Permission).where(Permission.code == code)
                )
            ).scalar_one_or_none()
            if existing is None:
                p = Permission(code=code, description=desc)
                session.add(p)
                await session.flush()
                perm_by_code[code] = p
            else:
                perm_by_code[code] = existing

        # Roles + permissions
        role_by_name: dict[str, Role] = {}
        for name, perm_codes in SEED_ROLES.items():
            existing = (
                await session.execute(select(Role).where(Role.name == name))
            ).scalar_one_or_none()
            role = existing or Role(name=name, description=f"Seed role: {name}")
            if existing is None:
                session.add(role)
                await session.flush()
            role_by_name[name] = role

            for code in perm_codes:
                rp_exists = (
                    await session.execute(
                        select(RolePermissions).where(
                            RolePermissions.role_id == role.id,
                            RolePermissions.permission_id == perm_by_code[code].id,
                        )
                    )
                ).scalar_one_or_none()
                if rp_exists is None:
                    session.add(
                        RolePermissions(
                            role_id=role.id,
                            permission_id=perm_by_code[code].id,
                        )
                    )

        # Users
        for u in SEED_USERS:
            existing = (
                await session.execute(select(User).where(User.email == u["email"]))
            ).scalar_one_or_none()
            if existing is None:
                session.add(User(**u))

        await session.commit()
        print(f"Seed complete: {len(SEED_PERMISSIONS)} permissions, "
              f"{len(SEED_ROLES)} roles, {len(SEED_USERS)} users.")


if __name__ == "__main__":
    asyncio.run(seed())