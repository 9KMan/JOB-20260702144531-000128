"""Stack-import smoke tests.

Verifies that every public module the platform exposes can be
imported cleanly — catches typos and circular imports early.
"""

from __future__ import annotations

import importlib

import pytest

PUBLIC_MODULES = [
    "app.main",
    "app.config",
    "app.database",
    "app.dependencies",
    "app.api.tasks",
    "app.api.agents",
    "app.api.runs",
    "app.api.review",
    "app.models",
    "app.orchestrator.ingest",
    "app.orchestrator.templates",
    "app.orchestrator.suggestions",
    "app.orchestrator.review",
    "app.orchestrator.audit",
    "app.orchestrator.identity",
    "app.orchestrator.workers",
    "app.observability.logging",
    "app.observability.tracing",
    "src.config",
    "src.database",
    "src.models",
]


@pytest.mark.parametrize("mod", PUBLIC_MODULES)
def test_module_imports_clean(mod: str) -> None:
    """Each public module must import without raising."""
    importlib.import_module(mod)