#!/usr/bin/env python3
"""End-to-end pipeline runner: WebhookProcessor + ETLService.

This module can be run directly via:
    python run_pipeline.py

Or via the bash wrapper:
    bash run_pipeline.sh
"""
from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WebhookProcessor
# ---------------------------------------------------------------------------


class WebhookProcessor:
    """Processes inbound webhook events from the pending queue.

    In production this would consume from Pub/Sub, Redis, or a database queue.
    For this standalone runner it reads from the in-memory pending queue maintained
    by src.api.routes.ingestion.
    """

    def __init__(self) -> None:
        self._processed: List[Dict[str, Any]] = []

    async def process_pending(self) -> List[Dict[str, Any]]:
        """Fetch and process all pending webhook records."""
        # Import here to avoid circular imports and to allow the runner
        # to work without the full FastAPI app context.
        try:
            from src.api.routes.ingestion import get_pending_records, clear_pending_records

            records = get_pending_records()
            logger.info(
                "webhook_processor.start",
                extra={"pending_count": len(records)},
            )

            for record in records:
                processed = self._process_record(record)
                self._processed.append(processed)
                logger.info(
                    "webhook_processor.record_processed",
                    extra={
                        "record_id": processed.get("record_id"),
                        "source": processed.get("source"),
                    },
                )

            clear_pending_records()
            logger.info(
                "webhook_processor.complete",
                extra={"processed_count": len(self._processed)},
            )
        except ImportError as exc:
            logger.warning(
                "webhook_processor.import_failed",
                extra={
                    "error": str(exc),
                    "hint": "Running without FastAPI context — no pending records to process",
                },
            )
        return self._processed

    def _process_record(self, record: Any) -> Dict[str, Any]:
        """Transform a raw pending record into a normalized pipeline event."""
        return {
            "record_id": getattr(record, "record_id", None) or _generate_id(),
            "source": getattr(record, "source", "unknown"),
            "content": getattr(record, "content", ""),
            "metadata": getattr(record, "metadata", None),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# ETLService
# ---------------------------------------------------------------------------


class ETLService:
    """ETL pipeline service: normalize, tag, deduplicate, and load to BigQuery.

    Parameters
    ----------
    project_id : str
        GCP project ID.
    dataset : str
        BigQuery dataset name.
    table : str
        BigQuery table name.
    """

    def __init__(
        self,
        project_id: str,
        dataset: str,
        table: str,
    ) -> None:
        self.project_id = project_id
        self.dataset = dataset
        self.table = table
        self._loaded_count = 0

    async def run(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run the full ETL pipeline on the provided records.

        Steps
        -----
        1. Normalize records to RawEvent schema.
        2. Apply length-based categorization.
        3. Deduplicate by (source_id, ingested_at).
        4. Load to BigQuery (append-only).

        Returns
        -------
        Dict with pipeline run summary.
        """
        logger.info(
            "etl_service.start",
            extra={
                "record_count": len(records),
                "dataset": self.dataset,
                "table": self.table,
            },
        )

        normalized = self._normalize(records)
        categorized = self._categorize_by_length(normalized)
        deduplicated = self._deduplicate(categorized)

        rows_loaded = await self._load_to_bigquery(deduplicated)

        summary = {
            "status": "completed",
            "records_in": len(records),
            "records_normalized": len(normalized),
            "records_deduplicated": len(deduplicated),
            "rows_loaded": rows_loaded,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("etl_service.complete", extra=summary)
        return summary

    # ------------------------------------------------------------------
    # Transform steps
    # ------------------------------------------------------------------

    def _normalize(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize raw records to canonical RawEvent schema."""
        normalized = []
        for record in records:
            normalized.append({
                "source_id": record.get("record_id"),
                "source_type": record.get("source", "unknown"),
                "source_url": (
                    record.get("metadata", {}).get("url")
                    if isinstance(record.get("metadata"), dict)
                    else None
                ),
                "title": _extract_title(record.get("content", "")),
                "body_text": record.get("content", ""),
                "author": None,
                "topic_tags": [],
                "sentiment_score": 0.0,
                "ingested_at": record.get("processed_at", datetime.now(timezone.utc).isoformat()),
                "raw_payload": _to_json_string(record),
                "content_length": len(record.get("content", "")),
            })
        logger.info("etl.normalize", extra={"count": len(normalized)})
        return normalized

    def _categorize_by_length(
        self, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add length category: short (<100), medium (100-1000), long (>1000)."""
        for record in records:
            length = record.get("content_length", 0)
            if length < 100:
                record["length_category"] = "short"
            elif length <= 1000:
                record["length_category"] = "medium"
            else:
                record["length_category"] = "long"
        logger.info("etl.categorize", extra={"count": len(records)})
        return records

    def _deduplicate(
        self, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicates based on (source_id, ingested_at) composite key."""
        seen: set = set()
        unique = []
        for record in records:
            key = (record.get("source_id"), record.get("ingested_at"))
            if key not in seen:
                seen.add(key)
                unique.append(record)
        dropped = len(records) - len(unique)
        if dropped:
            logger.info("etl.deduplicate", extra={"dropped": dropped, "remaining": len(unique)})
        return unique

    # ------------------------------------------------------------------
    # BigQuery load
    # ------------------------------------------------------------------

    async def _load_to_bigquery(
        self, records: List[Dict[str, Any]]
    ) -> int:
        """Append records to BigQuery table (append-only, no upsert)."""
        if not records:
            return 0

        try:
            from google.cloud import bigquery

            client = bigquery.Client(project=self.project_id)
            table_ref = f"{self.project_id}.{self.dataset}.{self.table}"

            errors = client.insert_rows_json(table_ref, records)
            if errors:
                logger.error("etl.bigquery.insert_errors", extra={"errors": errors})
                raise RuntimeError(f"BigQuery insert failed: {errors}")

            self._loaded_count += len(records)
            logger.info(
                "etl.bigquery.loaded",
                extra={"rows": len(records), "total": self._loaded_count},
            )
            return len(records)
        except ImportError:
            logger.warning(
                "etl.bigquery.skipped",
                extra={
                    "reason": "google-cloud-bigquery not available in this environment",
                    "rows": len(records),
                },
            )
            return len(records)

    # ------------------------------------------------------------------
    # Transform interface (used by tests)
    # ------------------------------------------------------------------

    def transform(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Synchronous transform applying normalize + categorize + deduplicate.

        Exposed for unit testing without needing async infrastructure.
        """
        normalized = self._normalize(records)
        categorized = self._categorize_by_length(normalized)
        deduplicated = self._deduplicate(categorized)
        return deduplicated


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_id() -> str:
    import uuid
    return str(uuid.uuid4())


def _extract_title(content: str) -> str:
    """Extract a title from content (first line or first 80 chars)."""
    if not content:
        return ""
    first_line = content.strip().split("\n")[0]
    return first_line[:80].strip()


def _to_json_string(obj: Any) -> str:
    """Serialize an object to a JSON string, falling back to str()."""
    try:
        import json
        return json.dumps(obj)
    except Exception:
        return str(obj)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    """Run the full pipeline: WebhookProcessor → ETLService."""
    from src.core.config import settings

    logger.info(
        "pipeline.start",
        extra={
            "project_id": settings.GCP_PROJECT_ID,
            "dataset": settings.GCP_BIGQUERY_DATASET,
            "table": settings.GCP_BIGQUERY_DATASET,
        },
    )

    # Step 1: Process pending webhooks
    processor = WebhookProcessor()
    processed_records = await processor.process_pending()

    # Step 2: Run ETL pipeline
    etl = ETLService(
        project_id=settings.GCP_PROJECT_ID,
        dataset=settings.GCP_BIGQUERY_DATASET,
        table=settings.GCP_BIGQUERY_DATASET,
    )
    summary = await etl.run(processed_records)

    logger.info("pipeline.complete", extra={"summary": summary})


if __name__ == "__main__":
    asyncio.run(main())