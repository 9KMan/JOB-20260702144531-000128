"""BigQuery client wrapper with a graceful in-memory fallback for local/dev runs.

This module never hardcodes credentials; it uses GOOGLE_APPLICATION_CREDENTIALS
or the Application Default Credentials (ADC) chain.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Sequence

from src.core.config import settings

logger = logging.getLogger(__name__)


class BigQueryClient:
    """Async-friendly wrapper around google-cloud-bigquery.

    If the BigQuery client cannot be instantiated (no credentials in dev), the
    wrapper falls back to a deterministic in-memory dataset so the rest of the
    stack still functions.
    """

    def __init__(self) -> None:
        self._client: Any = None
        self._fallback: Dict[str, List[Dict[str, Any]]] = {}
        self._fallback_lock = asyncio.Lock()
        self._disabled = False
        self._init_client()

    def _init_client(self) -> None:
        if not settings.ENABLE_BIGQUERY_SYNC:
            logger.info("BigQuery sync disabled via config — using fallback data only")
            self._disabled = True
            return

        creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS or os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )
        if not creds_path or not os.path.exists(creds_path):
            logger.warning(
                "No GOOGLE_APPLICATION_CREDENTIALS found; falling back to in-memory data"
            )
            self._disabled = True
            return

        try:
            from google.cloud import bigquery  # type: ignore

            self._client = bigquery.Client(project=settings.GCP_PROJECT_ID)
            logger.info("BigQuery client initialised for project %s", settings.GCP_PROJECT_ID)
        except Exception as exc:  # pragma: no cover - depends on env
            logger.exception("Failed to init BigQuery client: %s", exc)
            self._disabled = True

    @property
    def is_live(self) -> bool:
        return self._client is not None and not self._disabled

    async def query(
        self,
        sql: str,
        parameters: Optional[Sequence[Dict[str, Any]]] = None,
        timeout: float = 30.0,
    ) -> List[Dict[str, Any]]:
        """Run a SQL query and return a list of dict rows."""
        if self.is_live:
            return await self._query_live(sql, parameters, timeout)
        return await self._query_fallback(sql, parameters)

    async def _query_live(
        self,
        sql: str,
        parameters: Optional[Sequence[Dict[str, Any]]],
        timeout: float,
    ) -> List[Dict[str, Any]]:
        from google.cloud import bigquery  # type: ignore

        job_config = bigquery.QueryJobConfig(query_parameters=list(parameters) if parameters else None)

        def _run() -> List[Dict[str, Any]]:
            job = self._client.query(sql, job_config=job_config)
            return [dict(row) for row in job.result(timeout=timeout)]

        return await asyncio.to_thread(_run)

    async def _query_fallback(
        self,
        sql: str,
        parameters: Optional[Sequence[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """Minimal deterministic in-memory SQL for dev / tests.

        Supports ``SELECT COUNT(*) / SELECT 1`` style probes only — anything
        more complex is a programming error in the dev environment.
        """
        async with self._fallback_lock:
            stripped = " ".join(sql.lower().split())
            if "select 1" in stripped or "select 1 as" in stripped:
                return [{"value": 1}]
            if "count(*)" in stripped:
                rows = self._fallback.setdefault("__count__", [{"n": 0}])
                return [{"n": len(rows)}]
            return self._fallback.get("__default__", [])

    async def load_table_from_dataframe(self, table_ref: str, rows: List[Dict[str, Any]]) -> int:
        """Insert rows into a BigQuery table (or fallback)."""
        if self.is_live:
            return await self._load_live(table_ref, rows)
        async with self._fallback_lock:
            self._fallback[table_ref] = list(rows)
        return len(rows)

    async def _load_live(self, table_ref: str, rows: List[Dict[str, Any]]) -> int:
        from google.cloud import bigquery  # type: ignore

        def _run() -> int:
            table = self._client.get_table(table_ref)
            errors = self._client.insert_rows_json(table, rows)
            if errors:
                raise RuntimeError(f"BigQuery insert errors: {errors}")
            return len(rows)

        return await asyncio.to_thread(_run)

    async def get_dataset_schema(self, dataset_id: str, table_name: str) -> Dict[str, Any]:
        """Return the BQ schema for a table, normalised to a serialisable dict."""
        if self.is_live:
            return await self._schema_live(dataset_id, table_name)
        return {"fields": [], "table": table_name, "dataset": dataset_id, "live": False}

    async def _schema_live(self, dataset_id: str, table_name: str) -> Dict[str, Any]:
        from google.cloud import bigquery  # type: ignore

        def _run() -> Dict[str, Any]:
            ref = self._client.dataset(dataset_id).table(table_name)
            table = self._client.get_table(ref)
            return {
                "dataset": dataset_id,
                "table": table_name,
                "fields": [
                    {"name": f.name, "type": f.field_type, "mode": f.mode}
                    for f in table.schema
                ],
                "live": True,
            }

        return await asyncio.to_thread(_run)


_singleton: Optional[BigQueryClient] = None


def get_bigquery_client() -> BigQueryClient:
    global _singleton
    if _singleton is None:
        _singleton = BigQueryClient()
    return _singleton
