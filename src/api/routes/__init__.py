"""API routes package."""

from src.api.routes.health import router as health
from src.api.routes.ingestion import router as ingest

__all__ = ["health", "ingest"]