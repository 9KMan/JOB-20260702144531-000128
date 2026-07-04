"""Human-in-the-loop review endpoints.

When the orchestrator generates a *suggestion* (e.g., a row mapping
for a new ingestion), it lands in the review queue. A human reviewer
then approves, rejects, or edits the suggestion. Every state change
is recorded as an immutable audit-log entry.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db_session
from src.models.user import User

router = APIRouter(prefix="/review", tags=["review"])


class SuggestionOut(BaseModel):
    """A suggestion awaiting review."""
    id: UUID
    kind: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    payload: dict
    created_at: datetime
    state: str  # pending_review, approved, rejected


class ReviewDecision(BaseModel):
    """A reviewer's decision on a suggestion."""
    decision: str = Field(..., pattern="^(approve|reject|edit)$")
    notes: Optional[str] = Field(default=None, max_length=2000)
    edits: Optional[dict] = None


@router.get("/queue", response_model=list[SuggestionOut])
async def list_pending(
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> list[SuggestionOut]:
    """List suggestions awaiting human review."""
    return []


@router.post("/{suggestion_id}/decide", response_model=SuggestionOut)
async def decide(
    suggestion_id: UUID,
    decision: ReviewDecision,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> SuggestionOut:
    """Record a reviewer's decision on a suggestion."""
    raise HTTPException(status_code=404, detail="Suggestion not found")