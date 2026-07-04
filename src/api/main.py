"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health, ingest
from src.core.config import settings
from src.core.logging import setup_logging

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Looker Studio Data Pipeline API", extra={"port": settings.API_PORT})
    yield
    logger.info("Shutting down Looker Studio Data Pipeline API")


app = FastAPI(
    title="Looker Studio Data Pipeline API",
    description="Ingest, ETL, and tag data from multiple sources into BigQuery",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])


@app.get("/status")
def status():
    """Return pipeline status."""
    return {
        "status": "operational",
        "project_id": settings.GCP_PROJECT_ID,
        "dataset": settings.GCP_BIGQUERY_DATASET,
        "table": settings.GCP_BIGQUERY_TABLE,
    }