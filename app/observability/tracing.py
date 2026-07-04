"""Distributed tracing setup.

OpenTelemetry is wired in only when ``settings.tracing_enabled`` is
True. When disabled (the default for local dev), this module is a
no-op so the rest of the app can still import it.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def configure_tracing(app: "FastAPI", enabled: bool) -> None:
    """Set up OpenTelemetry tracing on ``app`` if ``enabled`` is True."""
    if not enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
    except ImportError:
        # Telemetry deps not installed — skip silently.
        return

    provider = TracerProvider(resource=Resource.create({"service.name": "iap"}))
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)