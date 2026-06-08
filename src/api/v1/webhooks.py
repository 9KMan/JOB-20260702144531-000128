"""Webhook handlers for inbound events (BigQuery, Airflow, Looker Studio)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db import get_db
from src.models.webhook import WebhookEvent
from src.services.cache import get_cache
from src.services.webhook_security import verify_signature, webhook_secret_for

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_cache = get_cache()


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _unauthorized(detail: str = "invalid signature") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


async def _persist_event(
    session: AsyncSession,
    *,
    direction: str,
    source: str,
    event_type: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    signature: Optional[str],
    status_label: str = "received",
    error: Optional[str] = None,
) -> WebhookEvent:
    event = WebhookEvent(
        direction=direction,
        source=source,
        event_type=event_type,
        signature=signature,
        payload=payload,
        headers=headers,
        status=status_label,
        error=error,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def _verify_and_persist(
    request: Request,
    session: AsyncSession,
    source: str,
    event_type: str,
    signature_header: Optional[str],
) -> tuple[Dict[str, Any], WebhookEvent]:
    if not settings.ENABLE_WEBHOOKS:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "webhooks disabled")

    body = await request.body()
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        raise _bad_request(f"invalid JSON body: {exc}") from exc

    if not isinstance(payload, dict):
        raise _bad_request("payload must be a JSON object")

    secret = webhook_secret_for(source)
    if signature_header is None or not verify_signature(secret, body, signature_header):
        raise _unauthorized()

    event = await _persist_event(
        session,
        direction="inbound",
        source=source,
        event_type=event_type,
        payload=payload,
        headers={k: v for k, v in request.headers.items()},
        signature=signature_header,
        status_label="received",
    )
    return payload, event


@router.post(
    "/bigquery",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive BigQuery job-completion notifications",
)
async def bigquery_webhook(
    request: Request,
    background: BackgroundTasks,
    x_signature: Optional[str] = Header(default=None, alias="X-Signature"),
    x_event_type: Optional[str] = Header(default="job.completed", alias="X-Event-Type"),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    payload, event = await _verify_and_persist(
        request, session, source="bigquery", event_type=x_event_type, signature_header=x_signature
    )

    background.add_task(_invalidate_looker_cache, payload)
    return {"status": "accepted", "event_id": str(event.id)}


@router.post(
    "/airflow",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive Airflow DAG-run state change notifications",
)
async def airflow_webhook(
    request: Request,
    x_signature: Optional[str] = Header(default=None, alias="X-Signature"),
    x_event_type: Optional[str] = Header(default="dag_run.success", alias="X-Event-Type"),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    payload, event = await _verify_and_persist(
        request, session, source="airflow", event_type=x_event_type, signature_header=x_signature
    )
    return {"status": "accepted", "event_id": str(event.id), "dag_id": payload.get("dag_id")}


@router.post(
    "/looker",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive Looker Studio refresh-completion pings",
)
async def looker_webhook(
    request: Request,
    x_signature: Optional[str] = Header(default=None, alias="X-Signature"),
    x_event_type: Optional[str] = Header(default="report.refreshed", alias="X-Event-Type"),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    payload, event = await _verify_and_persist(
        request, session, source="looker_studio", event_type=x_event_type, signature_header=x_signature
    )
    return {"status": "accepted", "event_id": str(event.id), "report_id": payload.get("report_id")}


@router.get(
    "/events",
    summary="List recent webhook events (paginated)",
)
async def list_webhook_events(
    source: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from sqlalchemy import desc, select

    stmt = select(WebhookEvent).order_by(desc(WebhookEvent.created_at))
    if source:
        stmt = stmt.where(WebhookEvent.source == source)
    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    events = result.scalars().all()
    return {
        "items": [
            {
                "id": str(e.id),
                "direction": e.direction,
                "source": e.source,
                "event_type": e.event_type,
                "status": e.status,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
        "total": len(events),
    }


async def _invalidate_looker_cache(payload: Dict[str, Any]) -> None:
    """Background helper — wipe the dashboard cache after a BQ event."""
    report_id = payload.get("report_id") or payload.get("resource", {}).get("report_id")
    if report_id:
        await _cache.delete(f"dashboards:detail:{report_id}")
    await _cache.delete("dashboards:list")
    await _cache.delete("datasets:list")
