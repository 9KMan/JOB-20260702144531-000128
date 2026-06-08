"""BigQuery upsert helper."""
import logging
from datetime import datetime, timezone

import pandas as pd
from google.cloud import bigquery

from lib.config import settings

logger = logging.getLogger(__name__)


class BigQueryWriter:
    """Upsert DataFrame rows into BigQuery raw_data table."""

    def __init__(self):
        self.client = bigquery.Client()
        self.dataset = settings.GCP_BIGQUERY_DATASET
        self.table = settings.GCP_BIGQUERY_TABLE
        self.table_ref = '{}.{}.{}'.format(self.client.project, self.dataset, self.table)

    def ensure_table(self) -> None:
        """"Create the table with the required schema if it does not exist."""
        schema = [
            bigquery.SchemaField('id', 'STRING'),
            bigquery.SchemaField('source', 'STRING'),
            bigquery.SchemaField('content', 'STRING'),
            bigquery.SchemaField('title', 'STRING'),
            bigquery.SchemaField('url', 'STRING'),
            bigquery.SchemaField('tags', 'STRING'),
            bigquery.SchemaField('ingested_at', 'TIMESTAMP'),
            bigquery.SchemaField('processed_at', 'TIMESTAMP'),
            bigquery.SchemaField('dag_run_id', 'STRING'),
        ]
        table = bigquery.Table(self.table_ref, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning('DAY', field='ingested_at')
        table.clustering_fields = ['source']
        try:
            self.client.create_table(table, exists_ok=True)
            logger.info('Table %s ensured (created if missing)', self.table_ref)
        except Exception as exc:
            logger.warning('ensure_table failed: %s', exc)

    def upsert(self, df: pd.DataFrame, dag_run_id: str) -> int:
        """Load a DataFrame into BigQuery, returning the number of rows written."""
        if df.empty:
            logger.info('Empty DataFrame, skipping upsert')
            return 0

        df = df.copy()
        df['dag_run_id'] = dag_run_id
        if 'processed_at' not in df.columns:
            df['processed_at'] = datetime.now(timezone.utc)

        job_config = bigquery.LoadJobConfig(
            write_disposition='WRITE_APPEND',
            schema_update_options=['ALLOW_FIELD_ADDITION'],
            time_partitioning=bigquery.TimePartitioning('DAY', field='ingested_at'),
            clustering_fields=['source'],
        )
        job = self.client.load_table_from_dataframe(df, self.table_ref, job_config=job_config)
        job.result()
        output_rows = job.output_rows or len(df)
        logger.info('Upserted %d rows to %s', output_rows, self.table_ref)
        return output_rows
