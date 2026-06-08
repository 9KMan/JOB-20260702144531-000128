"""GCS blob write helper."""
import json
import logging
from datetime import datetime, timezone

from google.cloud import storage

from lib.config import settings

logger = logging.getLogger(__name__)


class GCSWriter:
    """Write JSON blobs to GCS atomically (write-to-tmp then rename)."""

    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.bucket(settings.GCS_BUCKET)

    def write_blob(self, payload: dict) -> str:
        """"Write a JSON payload to GCS and return the blob name."""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        blob_name = 'ingest/{}_{}.json'.format(timestamp, payload.get('id', 'unknown'))
        tmp_name = blob_name + '.tmp'

        blob = self.bucket.blob(tmp_name)
        blob.upload_from_string(json.dumps(payload), content_type='application/json')

        # Atomic rename by copying then deleting source
        new_blob = self.bucket.rename_blob(blob, blob_name.replace('ingest/', ''))
        logger.info('Wrote blob: %s', new_blob.name)
        return new_blob.name

    def list_blobs(self, prefix: str = 'ingest/') -> list[dict]:
        """List all blobs under the given prefix and return their JSON content."""
        blobs = list(self.bucket.list_blobs(prefix=prefix))
        records = []
        for blob in blobs:
            if blob.name.endswith('.tmp'):
                continue
            try:
                content = blob.download_as_text()
                records.append(json.loads(content))
            except Exception as exc:
                logger.warning('Failed to download blob %s: %s', blob.name, exc)
        return records

    def delete_blobs(self, blobs: list[dict]) -> int:
        """Delete blobs by name from the list of payload dicts."""
        deleted = 0
        for item in blobs:
            name = item.get('_blob_name')
            if not name:
                continue
            try:
                self.bucket.delete_blob(name)
                deleted += 1
            except Exception as exc:
                logger.warning('Failed to delete blob %s: %s', name, exc)
        return deleted
