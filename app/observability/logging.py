"""Structured-logging setup.

We use ``structlog`` everywhere — no ``print()`` calls in production
code. Logs are emitted as JSON for easy ingestion by Loki / CloudWatch.
"""

import logging
import sys
from typing import Any

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure ``structlog`` and the stdlib ``logging`` root logger.

    Idempotent — safe to call multiple times (e.g., from Celery workers
    that boot under a different process).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Route stdlib logging through structlog's renderer.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:
    """Return a structlog logger bound to ``name`` (typically __name__)."""
    return structlog.get_logger(name)