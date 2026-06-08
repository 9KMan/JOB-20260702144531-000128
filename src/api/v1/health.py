"""Health-check and readiness endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db import get_db
from src.schemas.common import HealthResponse
from src.services.bigquery_client import get_bigquery_client
from src.services.cache import get_cache

router = APIRouter(tags=["health"])


@router.get(
    "/healthz",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
)
async def healthz() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(tz=timezone.utc),
    )


@router.get(
    "/readyz",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe — checks DB, cache, BigQuery",
)
async def readyz(session: AsyncSession = Depends(get_db)) -> HealthResponse:
    deps: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        deps["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001
        deps["postgres"] = f"down: {exc}"

    cache = get_cache()
    deps["cache"] = "ok" if await cache.ping() else "down"

    bq = get_bigquery_client()
    deps["bigquery"] = "ok" if bq.is_live else "fallback"

    overall = "ok" if all(v.startswith("ok") or v == "fallback" for v in deps.values()) else "degraded"
    return HealthResponse(
        status=overall,
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(tz=timezone.utc),
        dependencies=deps,
    )
