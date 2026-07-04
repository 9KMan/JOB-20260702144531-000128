#!/usr/bin/env python3
"""Stack-import smoke test.

Loads every public symbol the platform exposes and verifies that
each one imports cleanly.  This catches typos and circular imports
before they hit a request.

Usage:
    python3 -m scripts.verify_stack
"""

from __future__ import annotations

import importlib
import sys
import traceback

from app.main import app


PUBLIC_MODULES = [
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


def main() -> int:
    """Walk every public module and confirm it imports."""
    failures: list[tuple[str, str]] = []
    for mod_name in PUBLIC_MODULES:
        try:
            importlib.import_module(mod_name)
            print(f"  ✓ {mod_name}")
        except Exception as e:
            failures.append((mod_name, str(e)))
            print(f"  ✗ {mod_name}: {e}")

    print()
    print(f"FastAPI app routes: {len(app.routes)}")
    if failures:
        print(f"\n{len(failures)} module(s) failed to import:")
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    print("\nAll modules importable. Stack verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())