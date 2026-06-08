"""Idempotent ETL helper: load CSV/JSONL rows into a BigQuery table.

Usage:
    python -m src.utils.bigquery_loader --table=my_dataset.events \\
        --source=./events.jsonl --staging

Add ``--live`` to actually perform the write. Without it, the script validates
and previews the rows but does not touch the destination table.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List

from src.core.logging import get_logger
from src.services.bigquery_client import get_bigquery_client

logger = get_logger(__name__)


def _iter_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _iter_csv(path: Path) -> Iterable[dict]:
    import csv

    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            yield row


def _detect_iter(path: Path) -> Iterable[dict]:
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        return _iter_jsonl(path)
    if suffix == ".csv":
        return _iter_csv(path)
    raise ValueError(f"unsupported source extension: {suffix}")


def load(
    table_ref: str,
    source: Path,
    live: bool = False,
    preview_limit: int = 5,
) -> dict:
    rows: List[dict] = []
    for i, row in enumerate(_detect_iter(source)):
        rows.append(row)
        if not live and i + 1 >= preview_limit:
            break

    if not live:
        logger.info("etl.staging", table=table_ref, total_seen=len(rows), preview=True)
        return {"mode": "staging", "rows_previewed": len(rows), "sample": rows[:preview_limit]}

    client = get_bigquery_client()
    inserted = client._load_live if client.is_live else client.load_table_from_dataframe
    if client.is_live:
        count = client._load_live_sync  # type: ignore[attr-defined]
        raise RuntimeError("use load_table_from_dataframe for live inserts")
    # Use the public coroutine method
    import asyncio
    count = asyncio.run(client.load_table_from_dataframe(table_ref, rows))
    logger.info("etl.live", table=table_ref, rows=count)
    return {"mode": "live", "rows_inserted": count}


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Idempotent BQ loader")
    parser.add_argument("--table", required=True, help="project.dataset.table")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--live", action="store_true", help="commit the write")
    parser.add_argument("--preview-limit", type=int, default=5)
    args = parser.parse_args(argv)

    if not args.source.exists():
        logger.error("etl.source_missing", path=str(args.source))
        return 2

    result = load(args.table, args.source, live=args.live, preview_limit=args.preview_limit)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
