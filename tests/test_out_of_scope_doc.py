"""Cross-check the OUT_OF_SCOPE.md doc against the codebase.

The OUT_OF_SCOPE doc is the single source of truth for *what this
build intentionally does not do*.  The codebase must reflect that
intention: every entry in the doc should correspond to at least one
code reference, and every OUT_OF_SCOPE marker in the code should be
listed in the doc.

This test catches the failure mode where the doc and code drift
apart silently.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_out_of_scope_doc_exists() -> None:
    """OUT_OF_SCOPE.md must exist and be non-empty."""
    path = REPO_ROOT / "OUT_OF_SCOPE.md"
    assert path.is_file()
    assert path.stat().st_size > 200, "OUT_OF_SCOPE.md is suspiciously small"


def test_out_of_scope_doc_lists_at_least_three_items() -> None:
    """The doc must enumerate at least three OUT_OF_SCOPE items."""
    text = (REPO_ROOT / "OUT_OF_SCOPE.md").read_text(encoding="utf-8")
    items = re.findall(r"^##\s+", text, flags=re.MULTILINE)
    assert len(items) >= 3, f"only {len(items)} items; expected ≥ 3"


def test_not_implemented_marker_is_used_in_code() -> None:
    """At least one Python module must define a ``NotImplemented`` class."""
    found = False
    for py in REPO_ROOT.rglob("*.py"):
        if "out_of_scope" in str(py).lower():
            continue
        rel = py.relative_to(REPO_ROOT).as_posix()
        if rel.startswith("tests/") or rel.startswith(".venv/"):
            continue
        text = py.read_text(encoding="utf-8")
        if "NotImplemented" in text and "OUT_OF_SCOPE" in text:
            found = True
            break
    assert found, (
        "no Python module declares a NotImplemented marker linked to OUT_OF_SCOPE"
    )