"""Run / execution endpoints.

A *run* is a single execution attempt of a task by a particular agent.
A task may have many runs over its lifetime (retries, replays). Runs
are immutable once they reach a terminal state.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db_session
from src.models.user import User

router = APIRouter(prefix="/runs", tags=["runs"])


class RunOut(BaseModel):
    """Response describing a run."""
    id: UUID
    task_id: UUID
    agent_id: Optional[str]
    state: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    error: Optional[str] = None


@router.get("", response_model=list[RunOut])
async def list_runs(
    task_id: Optional[UUID] = Query(default=None),
    state: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> list[RunOut]:
    """List runs, optionally filtered by task or state."""
    return []


@router.get("/{run_id}", response_model=RunOut)
async def get_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> RunOut:
    """Fetch a single run by ID."""
    raise HTTPException(status_code=404, detail="Run not found")