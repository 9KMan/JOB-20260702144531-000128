"""DAG: nightly ETL that loads raw events into the analytics warehouse."""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from src.core.logging import get_logger

logger = get_logger(__name__)

default_args = {
    "owner": "tuinui",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}


def _extract(**context) -> None:
    logger.info("etl.extract", ds=context["ds"])


def _transform(**context) -> None:
    logger.info("etl.transform", ds=context["ds"])


def _load(**context) -> None:
    logger.info("etl.load", ds=context["ds"])


def _notify(**context) -> None:
    webhook = os.environ.get("TUINUI_WEBHOOK_URL")
    if not webhook:
        return
    import httpx

    try:
        httpx.post(
            webhook,
            json={"event_type": "etl.completed", "ds": context["ds"]},
            timeout=10.0,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("etl.notify.failed", error=str(exc))


with DAG(
    dag_id="nightly_analytics_etl",
    description="Extract raw events, transform, and load to BigQuery",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval="0 2 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["etl", "bigquery", "nightly"],
) as dag:
    extract = PythonOperator(task_id="extract", python_callable=_extract, provide_context=True)
    transform = PythonOperator(task_id="transform", python_callable=_transform, provide_context=True)
    load = PythonOperator(task_id="load", python_callable=_load, provide_context=True)
    health_check = BashOperator(
        task_id="health_check",
        bash_command='echo "ETL completed for {{ ds }}"',
    )
    notify = PythonOperator(task_id="notify", python_callable=_notify, provide_context=True)

    extract >> transform >> load >> health_check >> notify
