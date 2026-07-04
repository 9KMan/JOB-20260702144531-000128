"""Shared pytest fixtures.

Kept intentionally minimal — the test suite is unit-test-heavy and
deliberately avoids any database connection (the smoke stack-test
covers wiring via ``scripts/verify_stack.py``).
"""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_ingested_rows() -> list[dict]:
    """A representative batch of ingested rows for testing."""
    return [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Carol", "email": "carol@example.com"},
    ]