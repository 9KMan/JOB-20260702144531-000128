"""Structured logging configuration using structlog + stdlib."""
import logging
import sys
from typing import Any, Dict

import structlog

from src.core.config import settings


def configure_logging() -> None:
    """Configure structlog + stdlib logging for JSON or console output."""
    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    timestamper = structlog.processors.TimeStamper(fmt="iso")

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.LOG_FORMAT == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Silence overly chatty libraries
    for noisy in ("uvicorn.access", "google.auth", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str, **bound: Any) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger with optional context."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    if bound:
        logger = logger.bind(**bound)
    return logger
