"""CRUD service for datasets with cache integration."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.dataset import Dataset
from src.schemas.dataset import DatasetCreate, DatasetUpdate
from src.services.cache import get_cache

logger = get_logger(__name__)
_cache = get_cache()

CACHE_TTL = 300  # seconds
CACHE_KEY_LIST = "datasets:list"
CACHE_KEY_DETAIL = "datasets:detail:{id}"


class DatasetNotFoundError(Exception):
    """Raised when a dataset id does not exist."""


async def invalidate_cache(dataset_id: Optional[uuid.UUID] = None) -> None:
    await _cache.delete(CACHE_KEY_LIST)
    if dataset_id is not None:
        await _cache.delete(CACHE_KEY_DETAIL.format(id=str(dataset_id)))


async def create_dataset(session: AsyncSession, payload: DatasetCreate) -> Dataset:
    obj = Dataset(**payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    await invalidate_cache()
    logger.info("dataset.created", dataset_id=str(obj.id), name=obj.name)
    return obj


async def get_dataset(session: AsyncSession, dataset_id: uuid.UUID) -> Dataset:
    cached = await _cache.get(CACHE_KEY_DETAIL.format(id=str(dataset_id)))
    if cached is not None:
        obj = Dataset(**cached)
        return obj

    result = await session.execute(select(Dataset).where(Dataset.id == dataset_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        raise DatasetNotFoundError(str(dataset_id))

    await _cache.set(
        CACHE_KEY_DETAIL.format(id=str(dataset_id)),
        _serialise(obj),
        ttl_seconds=CACHE_TTL,
    )
    return obj


async def list_datasets(session: AsyncSession, limit: int = 50, offset: int = 0) -> List[Dataset]:
    result = await session.execute(
        select(Dataset).order_by(Dataset.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


async def update_dataset(
    session: AsyncSession, dataset_id: uuid.UUID, payload: DatasetUpdate
) -> Dataset:
    obj = await get_dataset(session, dataset_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(obj, key, value)
    await session.commit()
    await session.refresh(obj)
    await invalidate_cache(dataset_id)
    logger.info("dataset.updated", dataset_id=str(dataset_id), changed=list(data))
    return obj


async def delete_dataset(session: AsyncSession, dataset_id: uuid.UUID) -> None:
    obj = await get_dataset(session, dataset_id)
    await session.delete(obj)
    await session.commit()
    await invalidate_cache(dataset_id)
    logger.info("dataset.deleted", dataset_id=str(dataset_id))


def _serialise(obj: Dataset) -> dict:
    from src.schemas.dataset import DatasetRead

    return DatasetRead.model_validate(obj).model_dump(mode="json")
