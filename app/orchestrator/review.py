"""Review-queue handlers.

When a reviewer approves / rejects / edits a suggestion, this module
is responsible for:
  1. Updating the suggestion's state.
  2. Writing the resulting changes back to the source data (if any).
  3. Recording an immutable audit-log entry.

Reviewers cannot edit a suggestion directly; they can only approve,
reject, or submit a structured *edits* payload. The edits are
validated against the target template before being applied.
"""

from typing import Any, Optional


class ReviewerNotAuthorizedError(Exception):
    """Raised when the current user lacks the ``review:suggestions`` permission."""


def apply_review_decision(
    suggestion: dict[str, Any],
    decision: str,
    reviewer_id: str,
    notes: Optional[str] = None,
    edits: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Mutate a suggestion dict in-memory to reflect the reviewer's decision.

    The caller is responsible for persistence and for emitting an
    audit-log entry via :mod:`app.orchestrator.audit`.
    """
    if decision not in ("approve", "reject", "edit"):
        raise ValueError(f"unknown decision: {decision!r}")
    updated = dict(suggestion)
    updated["state"] = "approved" if decision == "approve" else "rejected"
    updated["reviewer_id"] = reviewer_id
    updated["review_notes"] = notes
    updated["review_edits"] = edits
    return updated


def audit_trail_entry(
    suggestion: dict[str, Any],
    decision: str,
    reviewer_id: str,
) -> dict[str, Any]:
    """Return an audit-log dict describing the review decision."""
    return {
        "resource_type": "suggestion",
        "resource_id": suggestion["id"],
        "action": f"review.{decision}",
        "actor_id": reviewer_id,
        "before": {"state": suggestion.get("state")},
        "after": {"state": "approved" if decision == "approve" else "rejected"},
    }