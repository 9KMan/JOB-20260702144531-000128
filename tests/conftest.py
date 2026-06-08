"""Shared pytest fixtures.

Note: tests intentionally avoid hitting Postgres / BigQuery / Redis. The app
falls back to SQLite + in-memory when these services are unavailable.
"""
from __future__ import annotations

import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Force test-friendly env defaults BEFORE the app imports.
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("ENABLE_BIGQUERY_SYNC", "false")
os.environ.setdefault("ENABLE_WEBHOOKS", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="session")
def settings_overrides():
    return {
        "DEBUG": True,
        "ENABLE_BIGQUERY_SYNC": False,
        "ENABLE_WEBHOOKS": True,
    }


@pytest_asyncio.fixture
async def app_instance():
    from src.main import create_app

    return create_app()


@pytest_asyncio.fixture
async def client(app_instance) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
