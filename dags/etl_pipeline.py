"""Airflow DAG: ETL pipeline run every 12 hours."""
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from lib.config import settings
from lib.etl import process_blobs
from lib.ai_tagger import tag_records
from api.services.bigquery import BigQueryWriter
from api.services.gcs_writer import GCSWriter

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'pipeline',
    'retries': 2,
    'retry_delay': 600,
    'timeout': 7200,
    'execution_timeout': 7200,
}


def fetch_gcs_blobs(**context):
    """Fetch all ingest blobs from GCS and push their content to XCom."""
    gcs = GCSWriter()
    blobs = gcs.list_blobs(prefix='ingest/')
    logger.info('Found %d blobs to process', len(blobs))
    context['ti'].xcom_push(key='blobs', value=blobs)
    return blobs


def run_etl(**context):
    """ETL: normalise schema, deduplicate, apply AI tagging."""
    blobs = context['ti'].xcom_pull(key='blobs', task_ids='fetch_gcs_blobs')
    df = process_blobs(blobs)
    df = tag_records(df)
    logger.info('ETL produced %d rows', len(df))
    context['ti'].xcom_push(key='etl_df', value=df.to_dict(orient='records'))
    return len(df)


def upsert_bigquery(**context):
    """Upsert the processed DataFrame into BigQuery."""
    import pandas as pd
    records = context['ti'].xcom_pull(key='etl_df', task_ids='run_etl')
    if not records:
        logger.info('No records to upsert')
        return 0
    df = pd.DataFrame(records)
    writer = BigQueryWriter()
    writer.ensure_table()
    count = writer.upsert(df, dag_run_id=context['dag_run_id'])
    return count


def cleanup_gcs_blobs(**context):
    """Delete processed GCS blobs to avoid re-processing."""
    blobs = context['ti'].xcom_pull(key='blobs', task_ids='fetch_gcs_blobs')
    gcs = GCSWriter()
    deleted = gcs.delete_blobs(blobs)
    logger.info('Cleaned up %d blobs', deleted)
    return deleted


with DAG(
    dag_id='looker_etl_pipeline',
    default_args=default_args,
    description='Ingest text data, ETL, AI tag, and upsert to BigQuery every 12 hours',
    schedule_interval='*/12 * * * *',
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=['looker', 'etl', 'bigquery'],
) as dag:
    t_fetch = PythonOperator(task_id='fetch_gcs_blobs', python_callable=fetch_gcs_blobs, provide_context=True)
    t_etl = PythonOperator(task_id='run_etl', python_callable=run_etl, provide_context=True)
    t_upsert = PythonOperator(task_id='upsert_bigquery', python_callable=upsert_bigquery, provide_context=True)
    t_cleanup = PythonOperator(task_id='cleanup_gcs_blobs', python_callable=cleanup_gcs_blobs, provide_context=True)

    t_fetch >> t_etl >> t_upsert >> t_cleanup
