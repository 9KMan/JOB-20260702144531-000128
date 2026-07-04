"""Worker-process glue for Celery.

This module is intentionally tiny: it provides the Celery ``app``
object and a helper to enqueue a task by name. Actual task bodies
live in :mod:`app.orchestrator.ingest` and friends — we just
shuttle the work to the right queue.
"""

from typing import Any


# Lazy Celery import so that the rest of the orchestrator package
# can be imported in environments where Celery isn't installed
# (e.g., for unit tests that don't exercise the queue).
def _build_celery_app():
    try:
        from celery import Celery
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "Celery is not installed; install it via `pip install -r requirements.txt`"
        ) from e
    return Celery(
        "internal_automation_platform",
        broker="redis://localhost:6379/0",
        backend="redis://localhost:6379/1",
    )


# Module-level singletons; tests can monkeypatch ``celery_app``.
celery_app = None


def get_celery_app():
    """Lazy accessor for the Celery app singleton."""
    global celery_app
    if celery_app is None:
        celery_app = _build_celery_app()
    return celery_app


def enqueue(task_name: str, *args: Any, **kwargs: Any) -> str:
    """Enqueue a task by name and return its Celery task ID."""
    app = get_celery_app()
    result = app.send_task(task_name, args=args, kwargs=kwargs)
    return result.id