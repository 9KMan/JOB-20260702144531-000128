"""Health check endpoint."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: str
    service: str


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """
    Returns the health status of the API.

    Returns:
        HealthResponse with status, ISO timestamp, and service name.
    """
    logger.debug("Health check requested")
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        service="looker-studio-pipeline-api",
    )