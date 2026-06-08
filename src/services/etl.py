"""ETL service — transforms raw records and loads them into BigQuery."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.services.bigquery_client import BigQueryClient

logger = logging.getLogger(__name__)


class ETLService:
    """Orchestrates extract → transform → load for a given dataset.table."""

    def __init__(self, bq_client: BigQueryClient) -> None:
        self.bq_client = bq_client

    def transform_raw_data(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add length_category, word_count, and char_count to each record."""
        transformed: List[Dict[str, Any]] = []
        for record in records:
            text = record.get("text") or record.get("content") or ""
            word_count = len(text.split())
            char_count = len(text)
            if word_count < 10:
                length_category = "short"
            elif word_count < 50:
                length_category = "medium"
            else:
                length_category = "long"
            enriched = {**record, "word_count": word_count, "char_count": char_count, "length_category": length_category}
            transformed.append(enriched)
        return transformed

    async def run_etl(self, dataset: str, table: str, limit: int = 1000) -> int:
        """Run the full ETL pipeline, returning the number of rows loaded."""
        from src.services.ingestion import IngestionService

        api_sources = [{"url": "https://api.example.com/records"}]
        ingestion = IngestionService(api_sources)
        raw_records = await ingestion.fetch_all_apis()
        raw_records = raw_records[:limit]
        transformed = self.transform_raw_data(raw_records)
        table_ref = f"{dataset}.{table}"
        rows_loaded = await self.bq_client.load_table_from_dataframe(table_ref, transformed)
        logger.info("ETL complete: %d rows loaded into %s", rows_loaded, table_ref)
        return rows_loaded
