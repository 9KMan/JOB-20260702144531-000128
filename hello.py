"""BigQueryClient - Google BigQuery database client."""

from google.cloud import bigquery
from google.oauth2 import service_account


class BigQueryClient:
    """Google BigQuery client wrapper."""

    def __init__(
        self,
        project: str | None = None,
        credentials_path: str | None = None,
        credentials=None,
    ):
        """Initialize BigQuery client.

        Args:
            project: GCP project ID. Defaults to credentials.project.
            credentials_path: Path to service account JSON key file.
            credentials: Pre-configured google.auth.credentials.Credentials.
        """
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/bigquery"],
            )

        self._client = bigquery.Client(
            project=project,
            credentials=credentials,
        )

    def query(self, sql: str, params: list | None = None) -> list[dict]:
        """Execute a SQL query and return results as a list of dicts.

        Args:
            sql: SQL query string.
            params: Optional query parameters for parameterized queries.

        Returns:
            List of row dictionaries.
        """
        job_config = bigquery.QueryJobConfig()
        if params:
            job_config.query_parameters = params

        query_job = self._client.query(sql, job_config=job_config)
        results = query_job.result()
        return [dict(row) for row in results]

    def execute(self, sql: str, params: list | None = None) -> None:
        """Execute a SQL statement without returning results.

        Args:
            sql: SQL statement.
            params: Optional query parameters.
        """
        job_config = bigquery.QueryJobConfig()
        if params:
            job_config.query_parameters = params

        self._client.query(sql, job_config=job_config).result()

    def close(self) -> None:
        """Close the client connection."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()