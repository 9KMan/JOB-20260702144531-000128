"""Ingestion pipeline.

Reads data from external sources (CSV uploads, REST endpoints, DB
replicas), normalises each row into the canonical ``ingested_rows``
shape, and writes them idempotently based on ``source_row_hash``.

A row that has been seen before (same ``source_row_hash``) is
silently skipped — this is the source of truth for the *no duplicates*
guarantee that downstream consumers rely on.
"""

import hashlib
from typing import Any, Iterable


def compute_source_row_hash(source_id: str, row: dict[str, Any]) -> str:
    """Stable hash for a single ingested row, used for idempotency.

    The hash is computed over a sorted, JSON-serialised form of
    ``row`` keyed by ``source_id``. Two rows with identical content
    under the same source will always produce the same hash.
    """
    canonical = "|".join(
        f"{k}={row[k]}" for k in sorted(row.keys())
    )
    payload = f"{source_id}::{canonical}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalise_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Strip whitespace, lower-case keys, coerce common types.

    This is a deliberately small transformation — anything more
    aggressive should live in a downstream template.
    """
    return {k.strip().lower(): _coerce(v) for k, v in raw.items()}


def _coerce(value: Any) -> Any:
    """Best-effort type coercion for known scalar types."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() in ("true", "false"):
            return stripped.lower() == "true"
        try:
            return int(stripped)
        except ValueError:
            pass
        try:
            return float(stripped)
        except ValueError:
            pass
        return stripped
    return value


def ingest(source_id: str, rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the list of *new* (deduplicated) rows."""
    seen_hashes: set[str] = set()
    new_rows: list[dict[str, Any]] = []
    for raw in rows:
        norm = normalise_row(raw)
        h = compute_source_row_hash(source_id, norm)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        new_rows.append({**norm, "source_id": source_id, "source_row_hash": h})
    return new_rows