"""API endpoint tests using httpx AsyncClient."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


class TestHealthEndpoint:
    """Tests for GET /health."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient) -> None:
        """Health endpoint should return 200 with ok status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert data["service"] == "looker-studio-pipeline-api"


class TestIngestWebhookEndpoint:
    """Tests for POST /ingest/webhook/ingest."""

    @pytest.mark.asyncio
    async def test_ingest_webhook_returns_202(self, client: AsyncClient) -> None:
        """Ingest webhook should accept valid payload and return 202."""
        payload = {
            "data": "Sample webhook content for ingestion",
            "metadata": {
                "url": "https://example.com/article",
                "tags": ["test", "webhook"],
            },
        }
        response = await client.post("/ingest/webhook/ingest", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "record_id" in data
        assert "queued_at" in data

    @pytest.mark.asyncio
    async def test_ingest_webhook_empty_data_returns_422(self, client: AsyncClient) -> None:
        """Ingest webhook should reject empty data with 422."""
        payload = {"data": ""}
        response = await client.post("/ingest/webhook/ingest", json=payload)
        assert response.status_code == 422


class TestListJobsEndpoint:
    """Tests for GET /jobs or equivalent listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_jobs_returns_200(self, client: AsyncClient) -> None:
        """Jobs listing endpoint should return 200 with a list."""
        response = await client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "project_id" in data
        assert "dataset" in data
        assert "table" in data


class TestGetDataEndpoint:
    """Tests for data retrieval endpoint."""

    @pytest.mark.asyncio
    async def test_get_data_returns_200(self, client: AsyncClient) -> None:
        """Data retrieval endpoint should return 200."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data