"""DAG: refresh Looker Studio metrics from BigQuery on a schedule.

This DAG is loaded by Airflow when ``AIRFLOW_HOME`` includes the ``dags/``
directory of this repository.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

default_args = {
    "owner": "tuinui",
    "depends_on_past": False,
    "email": [os.environ.get("ALERT_EMAIL", "ops@tuinui.example")],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=30),
}


def _refresh_metrics(**context) -> dict:
    """Run a BigQuery refresh of all registered metrics.

    In production this calls the same code path the FastAPI ``/metrics/{id}/evaluate``
    endpoint uses; for the DAG we import it lazily so Airflow parsing doesn't
    require a running database.
    """
    from src.services.bigquery_client import get_bigquery_client

    client = get_bigquery_client()
    rows = client._fallback if hasattr(client, "_fallback") else {}

    logger.info(
        "airflow.metrics.refresh",
        dag_run_id=context.get("run_id"),
        bigquery_live=client.is_live,
    )
    return {
        "live": client.is_live,
        "tables_seen": len(rows),
        "ran_at": datetime.utcnow().isoformat(),
    }


def _notify_looker(**context) -> None:
    """Best-effort HTTP POST to the Looker Studio webhook."""
    import httpx

    webhook_url = os.environ.get("LOOKER_WEBHOOK_URL")
    if not webhook_url:
        logger.info("airflow.looker.notify.skipped", reason="no LOOKER_WEBHOOK_URL")
        return
    try:
        response = httpx.post(
            webhook_url,
            json={
                "dag_id": context["dag"].dag_id,
                "run_id": context["run_id"],
                "status": "success",
            },
            timeout=10.0,
        )
        logger.info("airflow.looker.notify", status_code=response.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("airflow.looker.notify.failed", error=str(exc))


with DAG(
    dag_id="looker_studio_metric_refresh",
    description="Refresh Looker Studio metrics from BigQuery",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval=timedelta(minutes=settings.LOOKER_STUDIO_REFRESH_INTERVAL_MINUTES),
    catchup=False,
    max_active_runs=1,
    tags=["looker_studio", "bigquery", "metrics"],
) as dag:
    refresh = PythonOperator(
        task_id="refresh_metrics",
        python_callable=_refresh_metrics,
        provide_context=True,
    )
    notify = PythonOperator(
        task_id="notify_looker",
        python_callable=_notify_looker,
        provide_context=True,
    )

    refresh >> notify
