"""Scheduler that runs the ETL pipeline every 12 hours."""
from __future__ import annotations

import asyncio
import logging

from src.services.bigquery_client import get_bigquery_client
from src.services.etl import ETLService

logger = logging.getLogger(__name__)


async def run_scheduled_etl() -> None:
    """Run the ETL pipeline every 12 hours (43200 seconds)."""
    bq_client = get_bigquery_client()
    etl = ETLService(bq_client)
    interval_seconds = 43200  # 12 hours
    while True:
        try:
            count = await etl.run_etl("dataset", "table", limit=1000)
            logger.info("Scheduled ETL completed: %d rows loaded", count)
        except Exception as exc:
            logger.exception("Scheduled ETL failed: %s", exc)
        await asyncio.sleep(interval_seconds)
