"""CRUD router for datasets."""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.schemas.common import Page
from src.schemas.dataset import DatasetCreate, DatasetRead, DatasetUpdate
from src.services import dataset_service

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post(
    "",
    response_model=DatasetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new BigQuery dataset",
)
async def create_dataset(
    payload: DatasetCreate,
    session: AsyncSession = Depends(get_db),
) -> DatasetRead:
    obj = await dataset_service.create_dataset(session, payload)
    return DatasetRead.model_validate(obj)


@router.get(
    "",
    response_model=Page[DatasetRead],
    summary="List registered datasets",
)
async def list_datasets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> Page[DatasetRead]:
    offset = (page - 1) * page_size
    items = await dataset_service.list_datasets(session, limit=page_size, offset=offset)
    total = len(items)
    return Page[DatasetRead](
        items=[DatasetRead.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        has_next=total == page_size,
    )


@router.get(
    "/{dataset_id}",
    response_model=DatasetRead,
    summary="Fetch a single dataset",
)
async def get_dataset(
    dataset_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> DatasetRead:
    try:
        obj = await dataset_service.get_dataset(session, dataset_id)
    except dataset_service.DatasetNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DatasetRead.model_validate(obj)


@router.patch(
    "/{dataset_id}",
    response_model=DatasetRead,
    summary="Update dataset metadata",
)
async def update_dataset(
    dataset_id: uuid.UUID,
    payload: DatasetUpdate,
    session: AsyncSession = Depends(get_db),
) -> DatasetRead:
    try:
        obj = await dataset_service.update_dataset(session, dataset_id, payload)
    except dataset_service.DatasetNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DatasetRead.model_validate(obj)


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a dataset",
)
async def delete_dataset(
    dataset_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    try:
        await dataset_service.delete_dataset(session, dataset_id)
    except dataset_service.DatasetNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
