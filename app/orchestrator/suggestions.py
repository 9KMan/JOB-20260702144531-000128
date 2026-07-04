"""Suggestion generation and lifecycle.

A *suggestion* is a proposed mapping from one ingested row to a
template output. Suggestions are created by the orchestrator, scored
on confidence, and either auto-approved (high confidence) or routed
to the human review queue (low confidence).
"""

from typing import Any
from uuid import uuid4


AUTO_APPROVE_THRESHOLD = 0.85


class NotImplementedInScopeError(NotImplementedError):
    """OUT_OF_SCOPE marker — see OUT_OF_SCOPE.md for the policy."""


def score_confidence(rule_scores: list[float]) -> float:
    """Combine per-rule scores into one overall confidence score.

    Currently a simple mean — kept as a function so future weighting
    schemes (e.g., per-rule criticality) can be swapped in.
    """
    if not rule_scores:
        return 0.0
    return sum(rule_scores) / len(rule_scores)


def should_auto_approve(confidence: float) -> bool:
    """Decide whether a suggestion can skip the human review queue."""
    return confidence >= AUTO_APPROVE_THRESHOLD


def make_suggestion(
    *,
    ingested_row_id: str,
    template_id: str,
    payload: dict[str, Any],
    confidence: float,
) -> dict[str, Any]:
    """Construct a suggestion dict (not yet persisted)."""
    return {
        "id": str(uuid4()),
        "ingested_row_id": ingested_row_id,
        "template_id": template_id,
        "payload": payload,
        "confidence": confidence,
        "state": "approved" if should_auto_approve(confidence) else "pending_review",
        "created_at": _now_iso(),
    }


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def advanced_ml_scorer(*args: Any, **kwargs: Any) -> float:
    """OUT_OF_SCOPE: advanced ML scoring (e.g., LLM-based).

    Per OUT_OF_SCOPE.md, ML-based confidence scoring is deferred to a
    future iteration.  This stub raises so that any code path that
    accidentally reaches it fails loudly.
    """
    raise NotImplementedInScopeError(
        "advanced_ml_scorer is OUT_OF_SCOPE — see OUT_OF_SCOPE.md"
    )