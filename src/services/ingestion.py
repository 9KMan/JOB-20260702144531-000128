"""API ingestion service — fetches records from configured external sources."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class IngestionService:
    """Fetches raw records from a list of API sources."""

    def __init__(self, api_sources: List[Dict[str, Any]]) -> None:
        self.api_sources = api_sources

    async def fetch_from_api(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch JSON records from a single URL using httpx.AsyncClient."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers or {})
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "results" in data:
                    return data["results"]
                return [data]
        except Exception as exc:
            logger.warning("Failed to fetch from %s: %s", url, exc)
            return []

    async def fetch_all_apis(self) -> List[Dict[str, Any]]:
        """Fetch records from all configured API sources concurrently."""
        tasks = [
            self.fetch_from_api(source.get("url", ""), source.get("headers"))
            for source in self.api_sources
            if source.get("url")
        ]
        results = await httpx.AsyncClient().gather(*tasks, return_exceptions=True)
        records: List[Dict[str, Any]] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("API fetch error: %s", result)
                continue
            records.extend(result)
        return records
