"""BigQuery schema loader — fetches, validates, and caches table schemas.

The module normalises BigQuery table schemas into a canonical internal format
that can be stored in the ``schema_json`` column of the ``datasets`` table and
used by transformation pipelines.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.services.bigquery_client import get_bigquery_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class BQField:
    """A single field in a BigQuery table schema."""

    name: str
    field_type: str  # STRING, INTEGER, FLOAT, BOOLEAN, TIMESTAMP, DATE, DATETIME, RECORD, etc.
    mode: str = "NULLABLE"  # NULLABLE, REQUIRED, REPEATED
    description: str = ""
    policy_tags: List[str] = field(default_factory=list)
    max_length: Optional[int] = None

    @classmethod
    def from_bq_api(cls, raw: Dict[str, Any]) -> "BQField":
        return cls(
            name=raw["name"],
            field_type=raw["type"].upper(),
            mode=raw.get("mode", "NULLABLE").upper(),
            description=raw.get("description", ""),
            policy_tags=raw.get("policyTags", {}).get("names", []),
            max_length=raw.get("maxLength"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.field_type,
            "mode": self.mode,
            "description": self.description,
            "policy_tags": self.policy_tags,
            "max_length": self.max_length,
        }


@dataclass
class TableSchema:
    """Normalised BigQuery table schema."""

    project: str
    dataset: str
    table: str
    fields: List[BQField] = field(default_factory=list)
    description: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    last_modified: Optional[datetime] = None
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    partition_enabled: bool = False
    clustering_enabled: bool = False
    clustering_fields: List[str] = field(default_factory=list)
    expiration_ms: Optional[int] = None
    loaded_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project": self.project,
            "dataset": self.dataset,
            "table": self.table,
            "fields": [f.to_dict() for f in self.fields],
            "description": self.description,
            "labels": self.labels,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "row_count": self.row_count,
            "size_bytes": self.size_bytes,
            "partition_enabled": self.partition_enabled,
            "clustering_enabled": self.clustering_enabled,
            "clustering_fields": self.clustering_fields,
            "expiration_ms": self.expiration_ms,
            "loaded_at": self.loaded_at.isoformat(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @property
    def table_ref(self) -> str:
        return f"{self.project}.{self.dataset}.{self.table}"

    @property
    def schema_hash(self) -> str:
        """Stable hash of the field list for change detection."""
        payload = json.dumps([f.to_dict() for f in self.fields], sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def get_field(self, name: str) -> Optional[BQField]:
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def has_field(self, name: str) -> bool:
        return any(f.name == name for f in self.fields)

    def field_names(self) -> List[str]:
        return [f.name for f in self.fields]

    def field_types(self) -> Dict[str, str]:
        return {f.name: f.field_type for f in self.fields}

    def is_temporal(self) -> bool:
        """True when the table has at least one TIMESTAMP/DATE/DATETIME field."""
        temporal = {"TIMESTAMP", "DATE", "DATETIME"}
        return any(f.field_type in temporal for f in self.fields)

    def is_partitioned(self) -> bool:
        return self.partition_enabled

    def is_clustered(self) -> bool:
        return self.clustering_enabled


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def load_dataset_schema(
    project: str,
    dataset: str,
    table: str,
    include_stats: bool = True,
) -> TableSchema:
    """Fetch and normalise the BigQuery schema for a table.

    Parameters
    ----------
    project:
        GCP project id.
    dataset:
        BigQuery dataset name.
    table:
        Table name (without project/dataset prefix).
    include_stats:
        When True, also fetch table metadata (row count, size, last modified).

    Returns
    -------
    TableSchema
        Normalised schema object.
    """
    bq = get_bigquery_client()
    raw = await bq.get_dataset_schema(dataset, table)

    if not raw.get("live", False):
        # Fallback: return an empty schema so the rest of the stack still works.
        logger.warning(
            "bigquery schema not available — using empty schema",
            extra={"project": project, "dataset": dataset, "table": table},
        )
        return TableSchema(project=project, dataset=dataset, table=table)

    raw_fields = raw.get("fields", [])
    fields = [BQField.from_bq_api(f) for f in raw_fields]

    schema = TableSchema(
        project=project,
        dataset=dataset,
        table=table,
        fields=fields,
        description=raw.get("description", ""),
        labels=raw.get("labels", {}),
        last_modified=raw.get("last_modified"),
        row_count=raw.get("row_count"),
        size_bytes=raw.get("size_bytes"),
        partition_enabled=raw.get("partition_enabled", False),
        clustering_enabled=raw.get("clustering_enabled", False),
        clustering_fields=raw.get("clustering_fields", []),
        expiration_ms=raw.get("expiration_ms"),
    )

    logger.info(
        "bigquery.schema.loaded",
        table_ref=schema.table_ref,
        field_count=len(fields),
        partitioned=schema.partition_enabled,
        clustered=schema.clustering_enabled,
    )
    return schema


def resolve_table_ref(
    project: Optional[str],
    dataset: str,
    table: str,
) -> str:
    """Build a fully-qualified ``project.dataset.table`` string.

    Parameters
    ----------
    project:
        Explicit project id, or None to use the configured default.
    dataset:
        BigQuery dataset name.
    table:
        Table name.

    Returns
    -------
    str
        ``project.dataset.table`` string.
    """
    effective_project = project or settings.GCP_PROJECT_ID
    return f"{effective_project}.{dataset}.{table}"


def schema_from_db_row(schema_json: Dict[str, Any]) -> TableSchema:
    """Reconstruct a TableSchema from a row stored in the datasets table."""
    fields = [BQField.from_bq_api(f) for f in schema_json.get("fields", [])]
    last_modified = schema_json.get("last_modified")
    if last_modified and isinstance(last_modified, str):
        last_modified = datetime.fromisoformat(last_modified)
    return TableSchema(
        project=schema_json.get("project", ""),
        dataset=schema_json.get("dataset", ""),
        table=schema_json.get("table", ""),
        fields=fields,
        description=schema_json.get("description", ""),
        labels=schema_json.get("labels", {}),
        last_modified=last_modified,
        row_count=schema_json.get("row_count"),
        size_bytes=schema_json.get("size_bytes"),
        partition_enabled=schema_json.get("partition_enabled", False),
        clustering_enabled=schema_json.get("clustering_enabled", False),
        clustering_fields=schema_json.get("clustering_fields", []),
        expiration_ms=schema_json.get("expiration_ms"),
    )
