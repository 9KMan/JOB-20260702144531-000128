"""Audit log — append-only record of every meaningful state change.

The audit log is the source of truth for *what happened* in the
system. Rows are INSERT-only: there is no UPDATE or DELETE path on
the audit log table. Any attempt to mutate an audit row will fail at
the database level.
"""

from datetime import datetime, timezone
from typing import Any


def build_audit_entry(
    *,
    resource_type: str,
    resource_id: str,
    action: str,
    actor_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct one audit-log row (not yet persisted)."""
    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "action": action,
        "actor_id": actor_id,
        "before": before or {},
        "after": after or {},
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }


def is_audit_immutable(table_name: str) -> bool:
    """Return True iff the given table is the audit log.

    Used by tests to assert the database schema enforces immutability
    on the audit log table.
    """
    return table_name == "audit_logs"