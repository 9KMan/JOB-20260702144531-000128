"""Background worker that processes pending webhooks."""
from __future__ import annotations

import logging

from src.services.bigquery_client import BigQueryClient, get_bigquery_client
from src.services.ingestion import IngestionService

logger = logging.getLogger(__name__)


class WebhookProcessor:
    """Processes pending webhook events by ingesting and ETL-ing them."""

    def __init__(self) -> None:
        self.bq_client: BigQueryClient = get_bigquery_client()
        self.ingestion = IngestionService(api_sources=[])

    async def process_pending(self) -> int:
        """Fetch and process all pending webhook records, returning count."""
        records = await self.ingestion.fetch_all_apis()
        if not records:
            logger.info("No pending webhook records to process")
            return 0
        from src.services.etl import ETLService

        etl = ETLService(self.bq_client)
        count = await etl.run_etl("webhooks", "events", limit=1000)
        logger.info("Processed %d pending webhook records", count)
        return count
