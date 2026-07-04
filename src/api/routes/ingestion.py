"""Ingestion endpoint for receiving text data from various sources."""
import logging
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status

from src.api.models.schemas import (
    IngestRequest,
    IngestResponse,
    WebhookPayload,
)
from src.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory queue for staging — in production, use a proper queue (Pub/Sub, Redis, etc.)
_pending_records: List[IngestRequest] = []


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_record(request: IngestRequest) -> IngestResponse:
    """
    Ingest a single text data record.

    Accepts raw text content from APIs, webhooks, or scraping tools.
    Records are staged in memory before the Airflow ETL pipeline picks them up.

    Args:
        request: IngestRequest with source, content, and optional metadata.

    Returns:
        IngestResponse with record_id and queued_at timestamp.

    Raises:
        HTTPException: 400 if content is empty or source is invalid.
    """
    if not request.content or not request.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="content cannot be empty",
        )

    if request.source not in ("api", "webhook", "scraper"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid source '{request.source}' — must be one of: api, webhook, scraper",
        )

    record_id = str(uuid.uuid4())
    queued_at = datetime.now(timezone.utc)

    logger.info(
        "Record ingested",
        extra={
            "record_id": record_id,
            "source": request.source,
            "content_length": len(request.content),
            "queued_at": queued_at.isoformat(),
        },
    )

    _pending_records.append(request)

    return IngestResponse(
        status="accepted",
        record_id=record_id,
        queued_at=queued_at.isoformat(),
    )


@router.post("/webhook/ingest", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_webhook(payload: WebhookPayload) -> IngestResponse:
    """
    Dedicated webhook receiver endpoint.

    Accepts a simplified webhook payload with a data field containing the content.

    Args:
        payload: WebhookPayload with data and optional metadata.

    Returns:
        IngestResponse with record_id and queued_at timestamp.
    """
    request = IngestRequest(
        source="webhook",
        content=payload.data,
        metadata=payload.metadata,
    )
    return ingest_record(request)


def get_pending_records() -> List[IngestRequest]:
    """Return all pending records staged for ETL processing."""
    return list(_pending_records)


def clear_pending_records() -> None:
    """Clear the pending records queue after ETL has consumed them."""
    _pending_records.clear()