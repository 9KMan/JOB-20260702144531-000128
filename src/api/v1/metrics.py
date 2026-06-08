"""CRUD + evaluation router for metrics."""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.schemas.metric import MetricCreate, MetricRead, MetricUpdate
from src.services import metric_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post(
    "",
    response_model=MetricRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new metric definition",
)
async def create_metric(
    payload: MetricCreate,
    session: AsyncSession = Depends(get_db),
) -> MetricRead:
    try:
        obj = await metric_service.create_metric(session, payload)
    except metric_service.DatasetMissingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"dataset not found: {exc}") from exc
    return MetricRead.model_validate(obj)


@router.get(
    "",
    response_model=List[MetricRead],
    summary="List metrics (optionally filtered by dataset)",
)
async def list_metrics(
    dataset_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> List[MetricRead]:
    items = await metric_service.list_metrics(session, dataset_id=dataset_id)
    return [MetricRead.model_validate(i) for i in items[offset : offset + limit]]


@router.get(
    "/{metric_id}",
    response_model=MetricRead,
    summary="Fetch a single metric",
)
async def get_metric(
    metric_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> MetricRead:
    try:
        obj = await metric_service.get_metric(session, metric_id)
    except metric_service.MetricNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return MetricRead.model_validate(obj)


@router.patch(
    "/{metric_id}",
    response_model=MetricRead,
    summary="Update a metric",
)
async def update_metric(
    metric_id: uuid.UUID,
    payload: MetricUpdate,
    session: AsyncSession = Depends(get_db),
) -> MetricRead:
    try:
        obj = await metric_service.update_metric(session, metric_id, payload)
    except metric_service.MetricNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return MetricRead.model_validate(obj)


@router.delete(
    "/{metric_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a metric",
)
async def delete_metric(
    metric_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    try:
        await metric_service.delete_metric(session, metric_id)
    except metric_service.MetricNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{metric_id}/evaluate",
    summary="Run the metric's BigQuery SQL and return its current value",
)
async def evaluate_metric(
    metric_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    try:
        result = await metric_service.evaluate_metric(session, metric_id)
    except metric_service.MetricNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return result
