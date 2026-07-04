"""FastAPI application entry-point for the ``app/`` plane.

Wires together:
  - the data layer (src.database)
  - HTTP routers (app.api.*)
  - observability hooks (app.observability.logging, tracing)
  - CORS middleware
  - request-level structured logging

This module is the **production** entry-point used by ``uvicorn`` and
``docker-compose up``.  It is intentionally distinct from
:mod:`src.main` (which is the CLI / migration smoke-test plane).
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.config import settings
from app.database import engine
from app.api.tasks import router as tasks_router
from app.api.agents import router as agents_router
from app.api.runs import router as runs_router
from app.api.review import router as review_router
from app.observability.logging import configure_logging
from app.observability.tracing import configure_tracing

logger = structlog.get_logger(__name__)


# CORS origin list — defaults to localhost dev; override via env in prod.
_DEFAULT_CORS = ["http://localhost:3000", "http://localhost:8000"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — runs startup / shutdown hooks."""
    configure_logging(getattr(settings, "log_level", "INFO"))
    configure_tracing(app, getattr(settings, "tracing_enabled", False))
    logger.info(
        "app.startup",
        app_name=getattr(settings, "app_name", "iap"),
        version=getattr(settings, "app_version", "0.1.0"),
    )
    yield
    logger.info("app.shutdown")
    await engine.dispose()


def create_app() -> FastAPI:
    """Construct the canonical ``app/``-plane FastAPI application."""
    app = FastAPI(
        title=getattr(settings, "app_name", "Internal Automation Platform"),
        description="Internal Automation Platform — ingestion, review, and audit.",
        version=getattr(settings, "app_version", "0.1.0"),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS — locked to the configured origin list (no wildcards in prod)
    cors_origins = getattr(settings, "cors_origins", None) or _DEFAULT_CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Emit one structured log line per HTTP request."""
        logger.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown",
        )
        response = await call_next(request)
        logger.info(
            "http.response",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        )
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all: log + return a 500 without leaking internals."""
        logger.exception("app.unhandled_exception", path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.get("/health", tags=["meta"])
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "plane": "app"}

    # Mount routers
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(agents_router, prefix="/api/v1")
    app.include_router(runs_router, prefix="/api/v1")
    app.include_router(review_router, prefix="/api/v1")

    return app


app = create_app()