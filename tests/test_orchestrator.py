"""Tests for the orchestrator modules (pure-Python, no HTTP)."""

from __future__ import annotations

import pytest

from app.orchestrator.ingest import (
    compute_source_row_hash,
    ingest,
    normalise_row,
)
from app.orchestrator.suggestions import (
    AUTO_APPROVE_THRESHOLD,
    NotImplementedInScopeError,
    advanced_ml_scorer,
    make_suggestion,
    score_confidence,
    should_auto_approve,
)
from app.orchestrator.review import apply_review_decision, audit_trail_entry
from app.orchestrator.templates import (
    TemplateNotFoundError,
    latest_active_version,
    validate_template_payload,
)
from app.orchestrator.audit import build_audit_entry, is_audit_immutable
from app.orchestrator.identity import (
    PERM_REVIEW_SUGGESTION,
    check_permission,
    has_permission,
)


def test_compute_source_row_hash_is_deterministic() -> None:
    """Same input → same hash, always."""
    row = {"a": 1, "b": 2}
    h1 = compute_source_row_hash("src1", row)
    h2 = compute_source_row_hash("src1", row)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest


def test_compute_source_row_hash_differs_per_source() -> None:
    """Different source_id → different hash even with same row."""
    row = {"a": 1}
    assert compute_source_row_hash("a", row) != compute_source_row_hash("b", row)


def test_normalise_row_lowercases_keys() -> None:
    """normalise_row should lowercase keys and strip whitespace."""
    out = normalise_row({" Name ": "Alice", " AGE ": "30"})
    assert "name" in out and "age" in out


def test_ingest_deduplicates() -> None:
    """ingest() should return only new (deduped) rows."""
    rows = [
        {"id": 1, "name": "Alice"},
        {"id": 1, "name": "Alice"},  # duplicate
        {"id": 2, "name": "Bob"},
    ]
    out = ingest("src1", rows)
    assert len(out) == 2


def test_score_confidence_average() -> None:
    """score_confidence returns the arithmetic mean."""
    assert score_confidence([0.5, 0.7, 0.9]) == pytest.approx(0.7)
    assert score_confidence([]) == 0.0


def test_should_auto_approve_threshold() -> None:
    """Confidence ≥ threshold → auto-approve."""
    assert should_auto_approve(AUTO_APPROVE_THRESHOLD) is True
    assert should_auto_approve(AUTO_APPROVE_THRESHOLD - 0.01) is False


def test_make_suggestion_high_confidence_auto_approves() -> None:
    """High confidence suggestion state should be 'approved'."""
    s = make_suggestion(
        ingested_row_id="row-1",
        template_id="tpl-1",
        payload={"x": 1},
        confidence=0.95,
    )
    assert s["state"] == "approved"


def test_make_suggestion_low_confidence_pending() -> None:
    """Low confidence suggestion state should be 'pending_review'."""
    s = make_suggestion(
        ingested_row_id="row-1",
        template_id="tpl-1",
        payload={"x": 1},
        confidence=0.5,
    )
    assert s["state"] == "pending_review"


def test_advanced_ml_scorer_raises_not_implemented() -> None:
    """OUT_OF_SCOPE stub must raise NotImplementedInScopeError."""
    with pytest.raises(NotImplementedInScopeError):
        advanced_ml_scorer()


def test_apply_review_decision_approve() -> None:
    """An approve decision sets state=approved."""
    out = apply_review_decision(
        suggestion={"id": "s1", "state": "pending_review"},
        decision="approve",
        reviewer_id="u1",
    )
    assert out["state"] == "approved"


def test_audit_trail_entry_shape() -> None:
    """audit_trail_entry returns a dict with required keys."""
    entry = audit_trail_entry(
        suggestion={"id": "s1", "state": "pending_review"},
        decision="approve",
        reviewer_id="u1",
    )
    assert entry["resource_type"] == "suggestion"
    assert entry["action"] == "review.approve"


def test_latest_active_version_returns_highest() -> None:
    """latest_active_version should return the highest-versioned active row."""
    versions = [
        {"version": 1, "status": "archived", "payload": {}},
        {"version": 2, "status": "active", "payload": {"x": 1}},
        {"version": 3, "status": "active", "payload": {"x": 2}},
    ]
    latest = latest_active_version("tpl-1", versions)
    assert latest is not None
    assert latest["version"] == 3


def test_validate_template_payload_rejects_empty_rules() -> None:
    """An empty rules list should produce a validation error."""
    errors = validate_template_payload({"inputs": [], "outputs": [], "rules": []})
    assert any("rules" in e for e in errors)


def test_build_audit_entry_includes_actor() -> None:
    """build_audit_entry should record who performed the action."""
    entry = build_audit_entry(
        resource_type="task",
        resource_id="t1",
        action="create",
        actor_id="u1",
    )
    assert entry["actor_id"] == "u1"


def test_is_audit_immutable_only_for_audit_logs() -> None:
    """is_audit_immutable should only return True for audit_logs."""
    assert is_audit_immutable("audit_logs") is True
    assert is_audit_immutable("users") is False


def test_has_permission_and_check() -> None:
    """has_permission / check_permission should agree."""
    assert has_permission(["task:create"], "task:create") is True
    assert has_permission(["task:create"], "review:suggestion") is False
    with pytest.raises(Exception):
        check_permission(["task:create"], PERM_REVIEW_SUGGESTION)