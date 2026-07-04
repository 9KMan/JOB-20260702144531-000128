"""FastAPI application bootstrap for the ``src/`` plane.

The canonical application lives in :mod:`app.main`. This module is the
``src/``-plane equivalent — it wires a minimal FastAPI app that the
migration tooling and CLI smoke tests can boot. It does NOT register
HTTP API routes (those live in :mod:`app.api`). It exists for the
``scripts/verify_stack.py`` smoke test and for ``alembic`` env wiring
that needs to import from a stable, FastAPI-aware module path.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy import text

from src.config import get_settings
from src.database import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup and shutdown."""
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Create the ``src/``-plane FastAPI application."""
    app = FastAPI(
        title=f"{settings.app_name} (src)",
        description="CLI + migrations plane bootstrap",
        version=settings.app_version,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "plane": "src"}

    @app.get("/health/db")
    async def database_health() -> dict[str, str]:
        """Database connectivity health check."""
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "plane": "src"}

    return app


app = create_app()
