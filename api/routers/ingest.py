"""Ingest endpoints: POST /ingest, POST /ingest/batch, POST /webhook."""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from api.models.schemas import IngestRecord, IngestResponse, BatchIngestRequest, WebhookPayload
from api.services.gcs_writer import GCSWriter

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/ingest', tags=['ingest'])
gcs = GCSWriter()


@router.post('', response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_record(record: IngestRecord) -> IngestResponse:
    """Receive a single text record and write it to GCS as a JSON blob."""
    payload = IngestRecord(
        id=str(uuid.uuid4()),
        source=record.source,
        content=record.content,
        title=record.title,
        url=record.url,
        ingested_at=datetime.now(timezone.utc),
    )
    try:
        blob_name = gcs.write_blob(payload.model_dump(mode='json'))
        logger.info('Ingested record %s from source %s', payload.id, payload.source)
        return IngestResponse(id=payload.id, blob_name=blob_name, status='accepted')
    except Exception as exc:
        logger.exception('Failed to ingest record')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post('/batch', response_model=list[IngestResponse], status_code=status.HTTP_201_CREATED)
async def ingest_batch(batch: BatchIngestRequest) -> list[IngestResponse]:
    """Receive multiple records at once and write them to GCS."""
    responses = []
    for record in batch.records:
        item = IngestRecord(
            id=str(uuid.uuid4()),
            source=record.source,
            content=record.content,
            title=record.title,
            url=record.url,
            ingested_at=datetime.now(timezone.utc),
        )
        try:
            blob_name = gcs.write_blob(item.model_dump(mode='json'))
            responses.append(IngestResponse(id=item.id, blob_name=blob_name, status='accepted'))
        except Exception as exc:
            logger.exception('Failed to ingest record %s', item.id)
            responses.append(IngestResponse(id=item.id, blob_name='', status='error'))
    return responses
