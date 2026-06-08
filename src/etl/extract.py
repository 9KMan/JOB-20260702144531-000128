import logging
from google.cloud import bigquery

def extract_data(project_id: str, dataset: str, table: str):
    client = bigquery.Client()
    query = f'SELECT * FROM {dataset}.{table} LIMIT 100'
    return client.query(query).to_dataframe()