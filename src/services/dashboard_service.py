"""CRUD service for dashboards."""
from __future__ import annotations

import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.dashboard import Dashboard
from src.models.dataset import Dataset
from src.schemas.dashboard import DashboardCreate, DashboardUpdate
from src.services.cache import get_cache

logger = get_logger(__name__)
_cache = get_cache()

CACHE_TTL = 300
CACHE_KEY_LIST = "dashboards:list"
CACHE_KEY_DETAIL = "dashboards:detail:{id}"


class DashboardNotFoundError(Exception):
    pass


class DatasetMissingError(Exception):
    pass


async def _invalidate(dashboard_id: uuid.UUID | None = None) -> None:
    await _cache.delete(CACHE_KEY_LIST)
    if dashboard_id is not None:
        await _cache.delete(CACHE_KEY_DETAIL.format(id=str(dashboard_id)))


async def create_dashboard(session: AsyncSession, payload: DashboardCreate) -> Dashboard:
    dataset = await session.get(Dataset, payload.dataset_id)
    if dataset is None:
        raise DatasetMissingError(str(payload.dataset_id))

    obj = Dashboard(
        title=payload.title,
        slug=payload.slug,
        description=payload.description,
        looker_url=payload.looker_url,
        config_json=payload.config_json,
        refresh_interval_minutes=payload.refresh_interval_minutes,
        is_published=payload.is_published,
        dataset_id=payload.dataset_id,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    await _invalidate()
    logger.info("dashboard.created", dashboard_id=str(obj.id), slug=obj.slug)
    return obj


async def get_dashboard(session: AsyncSession, dashboard_id: uuid.UUID) -> Dashboard:
    result = await session.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        raise DashboardNotFoundError(str(dashboard_id))

    obj.view_count = (obj.view_count or 0) + 1
    await session.commit()
    return obj


async def list_dashboards(
    session: AsyncSession, limit: int = 50, offset: int = 0, published_only: bool = False
) -> List[Dashboard]:
    stmt = select(Dashboard).order_by(Dashboard.created_at.desc())
    if published_only:
        stmt = stmt.where(Dashboard.is_published.is_(True))
    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_dashboard(
    session: AsyncSession, dashboard_id: uuid.UUID, payload: DashboardUpdate
) -> Dashboard:
    obj = await get_dashboard(session, dashboard_id)
    data = payload.model_dump(exclude_unset=True)
    if "dataset_id" in data and data["dataset_id"] is not None:
        exists = await session.get(Dataset, data["dataset_id"])
        if exists is None:
            raise DatasetMissingError(str(data["dataset_id"]))
    for key, value in data.items():
        setattr(obj, key, value)
    await session.commit()
    await session.refresh(obj)
    await _invalidate(dashboard_id)
    return obj


async def delete_dashboard(session: AsyncSession, dashboard_id: uuid.UUID) -> None:
    obj = await get_dashboard(session, dashboard_id)
    await session.delete(obj)
    await session.commit()
    await _invalidate(dashboard_id)
    logger.info("dashboard.deleted", dashboard_id=str(dashboard_id))
