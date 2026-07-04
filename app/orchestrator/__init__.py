"""Orchestration layer.

Each submodule owns one concern of the ingestion → suggestion →
review → audit pipeline. They are pure Python (no HTTP, no DB
session lifecycle) so they can be unit-tested and called from
Celery workers.
"""