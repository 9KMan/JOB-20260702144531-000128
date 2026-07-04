#!/usr/bin/env bash
# Start the Celery worker pool.
#
# Usage:
#   ./scripts/start_workers.sh [num_workers]
#
# Defaults to 2 workers. Override via the first positional arg.
set -euo pipefail

NUM_WORKERS="${1:-2}"
export PYTHONPATH="$(cd "$(dirname "$0")/.." && pwd):${PYTHONPATH:-}"

echo "Starting $NUM_WORKERS Celery worker(s)…"
exec celery -A app.orchestrator.workers.celery_app worker \
    --loglevel=INFO \
    --concurrency="$NUM_WORKERS"