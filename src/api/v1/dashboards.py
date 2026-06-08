"""CRUD router for dashboards."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.schemas.common import Page
from src.schemas.dashboard import DashboardCreate, DashboardRead, DashboardUpdate
from src.services import dashboard_service

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.post(
    "",
    response_model=DashboardRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Looker Studio dashboard definition",
)
async def create_dashboard(
    payload: DashboardCreate,
    session: AsyncSession = Depends(get_db),
) -> DashboardRead:
    try:
        obj = await dashboard_service.create_dashboard(session, payload)
    except dashboard_service.DatasetMissingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"dataset not found: {exc}") from exc
    return DashboardRead.model_validate(obj)


@router.get(
    "",
    response_model=Page[DashboardRead],
    summary="List dashboards",
)
async def list_dashboards(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    published_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
) -> Page[DashboardRead]:
    offset = (page - 1) * page_size
    items = await dashboard_service.list_dashboards(
        session, limit=page_size, offset=offset, published_only=published_only
    )
    return Page[DashboardRead](
        items=[DashboardRead.model_validate(i) for i in items],
        total=len(items),
        page=page,
        page_size=page_size,
        has_next=len(items) == page_size,
    )


@router.get(
    "/{dashboard_id}",
    response_model=DashboardRead,
    summary="Fetch a single dashboard",
)
async def get_dashboard(
    dashboard_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> DashboardRead:
    try:
        obj = await dashboard_service.get_dashboard(session, dashboard_id)
    except dashboard_service.DashboardNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DashboardRead.model_validate(obj)


@router.patch(
    "/{dashboard_id}",
    response_model=DashboardRead,
    summary="Update a dashboard",
)
async def update_dashboard(
    dashboard_id: uuid.UUID,
    payload: DashboardUpdate,
    session: AsyncSession = Depends(get_db),
) -> DashboardRead:
    try:
        obj = await dashboard_service.update_dashboard(session, dashboard_id, payload)
    except dashboard_service.DashboardNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except dashboard_service.DatasetMissingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"dataset not found: {exc}") from exc
    return DashboardRead.model_validate(obj)


@router.delete(
    "/{dashboard_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a dashboard",
)
async def delete_dashboard(
    dashboard_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    try:
        await dashboard_service.delete_dashboard(session, dashboard_id)
    except dashboard_service.DashboardNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
