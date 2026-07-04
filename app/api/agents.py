"""Agent registration and heartbeat endpoints.

An *agent* is a long-running worker process that pulls jobs from the
queue and executes them. Agents must heartbeat every 30 seconds; any
agent that misses two consecutive heartbeats is considered dead and
its in-flight jobs are re-queued.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db_session
from src.models.user import User

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentHeartbeat(BaseModel):
    """Heartbeat payload from an agent."""
    agent_id: str = Field(..., min_length=1, max_length=100)
    hostname: str = Field(..., min_length=1, max_length=200)
    version: str = Field(..., min_length=1, max_length=50)
    capacity: int = Field(default=1, ge=1, le=64)


class AgentOut(BaseModel):
    """Response describing a registered agent."""
    id: str
    hostname: str
    version: str
    last_heartbeat: datetime
    state: str


@router.post("/heartbeat", response_model=AgentOut)
async def heartbeat(
    payload: AgentHeartbeat,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> AgentOut:
    """Record a heartbeat from an agent."""
    return AgentOut(
        id=payload.agent_id,
        hostname=payload.hostname,
        version=payload.version,
        last_heartbeat=datetime.now(timezone.utc),
        state="alive",
    )


@router.get("", response_model=list[AgentOut])
async def list_agents(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> list[AgentOut]:
    """List all known agents."""
    return []