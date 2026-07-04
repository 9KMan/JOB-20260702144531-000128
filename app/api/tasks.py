"""Task lifecycle endpoints.

A *task* is the user-facing unit of work — it represents a request
to ingest data, generate suggestions, or perform some other
automation. Tasks are enqueued to the Celery worker pool and have a
linear state machine (pending → running → succeeded / failed / cancelled).
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db_session
from src.models.user import User

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    """Request payload for creating a new task."""
    name: str = Field(..., min_length=1, max_length=200)
    payload: dict = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)


class TaskOut(BaseModel):
    """Response payload describing a task."""
    id: UUID
    name: str
    state: str
    created_at: datetime


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> TaskOut:
    """Enqueue a new task."""
    return TaskOut(
        id=uuid4(),
        name=task.name,
        state="pending",
        created_at=datetime.now(timezone.utc),
    )


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    state: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> list[TaskOut]:
    """List tasks, optionally filtered by state."""
    return []


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> TaskOut:
    """Fetch a single task by ID."""
    raise HTTPException(status_code=404, detail="Task not found")


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> None:
    """Cancel a pending or running task."""
    return None