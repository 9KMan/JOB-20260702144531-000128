"""Shared pytest fixtures.

Two families of fixtures live here:

1. **Composio connector fixtures** (``mock_env``, ``mock_composio_client``,
   ``sample_ga4_response``, ``sample_realtime_response``, ``sample_oauth_token``):
   used by ``tests/connectors/test_ga4.py`` and friends.

2. **FastAPI app fixtures** (``app``, ``client``): used by ``tests/test_api.py``
   to drive the ingest/health/status routes through ``httpx.AsyncClient``.

The FastAPI fixtures are kept minimal — they do NOT mutate global state, so
running ``tests/test_api.py`` does not contaminate ``tests/connectors/`` env
mocks (those tests patch env vars themselves via the ``mock_env`` fixture).
"""
from __future__ import annotations

import os
from typing import Any, AsyncIterator, Dict
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Composio + connector fixtures (used by tests/connectors/test_ga4.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_env():
    """Fixture providing all required environment variables."""
    env_vars = {
        "COMPOSIO_API_KEY": "test_composio_api_key",
        "GOOGLE_CLIENT_ID": "test_google_client_id",
        "GOOGLE_CLIENT_SECRET": "test_google_client_secret",
        "GOOGLE_REDIRECT_URI": "http://localhost:8080/oauth/callback",
        "GOOGLE_GA4_PROPERTY_ID": "123456789",
        "HUBSPOT_API_KEY": "test_hubspot_api_key",
        "SLACK_BOT_TOKEN": "«redacted:xox…»",
        "SEMRUSH_API_KEY": "test_semrush_api_key",
        "POSTHOG_API_KEY": "test_posthog_api_key",
        "POSTHOG_PROJECT_ID": "test_project_id",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        yield env_vars


@pytest.fixture
def mock_composio_client():
    """Fixture providing a mock Composio client."""
    mock_client = MagicMock()

    mock_toolset = MagicMock()
    mock_toolset.execute.return_value = {
        "rows": [
            {"date": "2024-01-01", "sessions": 1000, "users": 800},
            {"date": "2024-01-02", "sessions": 1200, "users": 950},
        ],
        "totals": {"sessions": 2200, "users": 1750},
    }

    mock_client.get_toolset.return_value = mock_toolset

    with patch("src.connectors.google.ga4.Composio", return_value=mock_client):
        with patch("src.connectors.google.search_console.Composio", return_value=mock_client):
            with patch("src.connectors.google.ads.Composio", return_value=mock_client):
                with patch("src.connectors.hubspot.Composio", return_value=mock_client):
                    with patch("src.connectors.slack.Composio", return_value=mock_client):
                        with patch("src.connectors.semrush.Composio", return_value=mock_client):
                            with patch("src.connectors.posthog.Composio", return_value=mock_client):
                                yield mock_client


@pytest.fixture
def sample_ga4_response() -> Dict[str, Any]:
    """Fixture providing sample GA4 report response data."""
    return {
        "success": True,
        "data": {
            "rows": [
                {
                    "dimensionValues": [
                        {"value": "20240101", "name": "date"},
                        {"value": "United States", "name": "country"},
                    ],
                    "metricValues": [
                        {"value": "1000", "name": "sessions"},
                        {"value": "800", "name": "activeUsers"},
                    ],
                },
                {
                    "dimensionValues": [
                        {"value": "20240102", "name": "date"},
                        {"value": "Canada", "name": "country"},
                    ],
                    "metricValues": [
                        {"value": "500", "name": "sessions"},
                        {"value": "400", "name": "activeUsers"},
                    ],
                },
            ],
            "totals": [
                {
                    "metricValues": [
                        {"value": "1500", "name": "sessions"},
                        {"value": "1200", "name": "activeUsers"},
                    ],
                },
            ],
            "rowCount": 2,
            "metadata": {
                "propertyId": "123456789",
                "currencyCode": "USD",
                "timeZone": "America/New_York",
            },
        },
    }


@pytest.fixture
def sample_realtime_response() -> Dict[str, Any]:
    """Fixture providing sample GA4 realtime users response."""
    return {
        "success": True,
        "data": {
            "activeUsers": 42,
            "propertyId": "123456789",
        },
    }


@pytest.fixture
def sample_oauth_token() -> Dict[str, Any]:
    """Fixture providing sample OAuth token data."""
    return {
        "access_token": "test_access_token_12345",
        "refresh_token": "test_refresh_token_67890",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "https://www.googleapis.com/auth/analytics.readonly",
    }


# ---------------------------------------------------------------------------
# FastAPI app fixtures (used by tests/test_api.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """FastAPI app instance for direct endpoint testing.

    Importing lazily so that ``tests/connectors/`` (which only need Composio
    fixtures) don't pay the FastAPI import cost.
    """
    from src.api.main import app as fastapi_app

    return fastapi_app


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    """Async httpx client wired to the FastAPI app via ASGITransport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac