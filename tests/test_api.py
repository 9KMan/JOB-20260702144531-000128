"""Tests for the HTTP API surface.

Uses FastAPI's TestClient against the canonical app.  Most endpoints
require auth (which is stubbed); these tests cover the route-shape
contract only — happy-path JSON shape + status codes.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    """The /health endpoint should return 200 with status=healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "plane": "app"}


def test_openapi_spec_served() -> None:
    """The /openapi.json endpoint should expose the spec."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["info"]["title"]


def test_tasks_routes_require_auth() -> None:
    """All /api/v1/* routes require an authenticated user."""
    response = client.get("/api/v1/tasks")
    # Stub auth: 401 because no Authorization header.
    assert response.status_code in (401, 403)


def test_agents_heartbeat_route_registered() -> None:
    """The heartbeat route should be discoverable in OpenAPI."""
    response = client.get("/openapi.json")
    spec = response.json()
    paths = spec["paths"].keys()
    assert any("agents/heartbeat" in p for p in paths)


def test_review_queue_route_registered() -> None:
    """The review-queue route should be discoverable in OpenAPI."""
    response = client.get("/openapi.json")
    spec = response.json()
    paths = spec["paths"].keys()
    assert any("review/queue" in p for p in paths)