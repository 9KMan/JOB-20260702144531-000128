"""FastAPI dependency providers for the ``app/`` plane.

Centralises the most-used dependencies (DB session, current user,
RBAC checks) so that routers stay thin.
"""

from typing import AsyncIterator, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory
from app.models.user import User


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield an async SQLAlchemy session, ensuring cleanup."""
    async with async_session_factory() as session:
        yield session


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Resolve the authenticated user from a Bearer token.

    This is a stub — the real implementation will validate a JWT or
    SSO assertion.  For now, when ``settings.dev_bypass_auth`` is set,
    a synthetic ``dev@local`` user is returned.
    """
    if getattr(settings, "dev_bypass_auth", False):
        from sqlalchemy import select

        result = await db.execute(
            select(User).where(User.email == "dev@local")
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Dev user not seeded — run scripts/seed_dev.py",
            )
        return user

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Real token validation would happen here.  For now, reject.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token validation not implemented in this build",
    )