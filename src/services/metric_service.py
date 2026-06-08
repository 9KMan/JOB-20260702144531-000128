"""CRUD + BigQuery evaluation service for metrics."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.dataset import Dataset
from src.models.metric import Metric
from src.schemas.metric import MetricCreate, MetricUpdate
from src.services.bigquery_client import get_bigquery_client
from src.services.cache import get_cache

logger = get_logger(__name__)
_cache = get_cache()

CACHE_TTL = 120
CACHE_KEY_VALUE = "metrics:value:{id}"


class MetricNotFoundError(Exception):
    pass


class DatasetMissingError(Exception):
    pass


async def create_metric(session: AsyncSession, payload: MetricCreate) -> Metric:
    dataset = await session.get(Dataset, payload.dataset_id)
    if dataset is None:
        raise DatasetMissingError(str(payload.dataset_id))

    obj = Metric(
        name=payload.name,
        label=payload.label,
        description=payload.description,
        sql_expression=payload.sql_expression,
        aggregation=payload.aggregation,
        unit=payload.unit,
        format_pattern=payload.format_pattern,
        meta_json=payload.meta_json,
        dataset_id=payload.dataset_id,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    logger.info("metric.created", metric_id=str(obj.id), name=obj.name)
    return obj


async def list_metrics(session: AsyncSession, dataset_id: uuid.UUID | None = None) -> List[Metric]:
    stmt = select(Metric).order_by(Metric.created_at.desc())
    if dataset_id is not None:
        stmt = stmt.where(Metric.dataset_id == dataset_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_metric(session: AsyncSession, metric_id: uuid.UUID) -> Metric:
    obj = await session.get(Metric, metric_id)
    if obj is None:
        raise MetricNotFoundError(str(metric_id))
    return obj


async def update_metric(
    session: AsyncSession, metric_id: uuid.UUID, payload: MetricUpdate
) -> Metric:
    obj = await get_metric(session, metric_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(obj, key, value)
    await session.commit()
    await session.refresh(obj)
    await _cache.delete(CACHE_KEY_VALUE.format(id=str(metric_id)))
    return obj


async def delete_metric(session: AsyncSession, metric_id: uuid.UUID) -> None:
    obj = await get_metric(session, metric_id)
    await session.delete(obj)
    await session.commit()
    await _cache.delete(CACHE_KEY_VALUE.format(id=str(metric_id)))


async def evaluate_metric(session: AsyncSession, metric_id: uuid.UUID) -> Metric:
    """Run the metric's BigQuery SQL and cache the latest scalar value."""
    cache_key = CACHE_KEY_VALUE.format(id=str(metric_id))
    cached = await _cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    obj = await get_metric(session, metric_id)
    bq = get_bigquery_client()
    rows = await bq.query(f"SELECT {obj.aggregation}({obj.sql_expression}) AS value LIMIT 1")
    value = float(rows[0]["value"]) if rows and rows[0].get("value") is not None else None

    obj.last_value = value
    obj.last_calculated_at = datetime.now(tz=timezone.utc)
    await session.commit()
    await session.refresh(obj)

    result = {
        "metric_id": str(obj.id),
        "name": obj.name,
        "value": value,
        "calculated_at": obj.last_calculated_at.isoformat(),
    }
    await _cache.set(cache_key, result, ttl_seconds=CACHE_TTL)
    logger.info("metric.evaluated", metric_id=str(obj.id), value=value)
    return result
