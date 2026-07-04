"""Tests that the project structure matches the documented layout.

The repo must contain every directory and file the SPEC promises —
no missing pieces, no rogue files.  This is a structural guard
against partial builds.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


REQUIRED_DIRS = [
    "src",
    "src/models",
    "app",
    "app/api",
    "app/orchestrator",
    "app/models",
    "app/schemas",
    "app/observability",
    "app/ui",
    "alembic",
    "alembic/versions",
    "scripts",
    "tests",
    "diagrams",
    "db",
    "db/migrations",
]


REQUIRED_FILES = [
    "pyproject.toml",
    "requirements.txt",
    "docker-compose.yml",
    "Dockerfile",
    ".env.example",
    "README.md",
    "OUT_OF_SCOPE.md",
    "SPEC.md",
    "alembic.ini",
    "alembic/env.py",
    "alembic/script.py.mako",
    "alembic/versions/001_initial.py",
    "src/__init__.py",
    "src/config.py",
    "src/database.py",
    "src/main.py",
    "src/models/__init__.py",
    "src/models/base.py",
    "src/models/user.py",
    "src/models/role.py",
    "src/models/ingested_row.py",
    "src/models/template.py",
    "src/models/suggestion.py",
    "src/models/audit_log.py",
    "src/models/session.py",
    "app/__init__.py",
    "app/config.py",
    "app/database.py",
    "app/main.py",
    "app/dependencies.py",
    "app/api/__init__.py",
    "app/api/tasks.py",
    "app/api/agents.py",
    "app/api/runs.py",
    "app/api/review.py",
    "app/orchestrator/__init__.py",
    "app/orchestrator/ingest.py",
    "app/orchestrator/templates.py",
    "app/orchestrator/suggestions.py",
    "app/orchestrator/review.py",
    "app/orchestrator/audit.py",
    "app/orchestrator/identity.py",
    "app/orchestrator/workers.py",
    "app/models/__init__.py",
    "app/models/base.py",
    "app/models/user.py",
    "app/models/role.py",
    "app/models/ingested_row.py",
    "app/models/template.py",
    "app/models/suggestion.py",
    "app/models/audit_log.py",
    "app/models/session.py",
    "app/schemas/__init__.py",
    "app/schemas/base.py",
    "app/observability/__init__.py",
    "app/observability/logging.py",
    "app/observability/tracing.py",
    "app/ui/__init__.py",
    "scripts/__init__.py",
    "scripts/seed_dev.py",
    "scripts/start_workers.sh",
    "scripts/verify_stack.py",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/test_api.py",
    "tests/test_orchestrator.py",
    "tests/test_project_structure.py",
    "tests/test_stack_imports.py",
    "tests/test_out_of_scope_doc.py",
    "diagrams/architecture.svg",
    "diagrams/workflow.svg",
    "diagrams/project-structure.svg",
]


@pytest.mark.parametrize("path", REQUIRED_DIRS)
def test_required_directory_exists(path: str) -> None:
    """Every directory the SPEC promises must exist."""
    assert (REPO_ROOT / path).is_dir(), f"missing directory: {path}"


@pytest.mark.parametrize("path", REQUIRED_FILES)
def test_required_file_exists(path: str) -> None:
    """Every file the SPEC promises must exist."""
    assert (REPO_ROOT / path).is_file(), f"missing file: {path}"


def test_no_ascii_art_in_markdown_files() -> None:
    """Top-level .md files must be free of Unicode box-drawing characters.

    Only scans files at the repo root and in `diagrams/` /
    `docs/` / `scripts/` — does not descend into ``.planning/``
    or ``.venv/``, which are pre-existing build artifacts.
    """
    scan_roots = [REPO_ROOT, REPO_ROOT / "diagrams"]
    allowed_dirs = {"diagrams", "docs", "scripts"}
    offenders: list[str] = []
    for root in scan_roots:
        if not root.exists():
            continue
        for md in root.rglob("*.md"):
            rel = md.relative_to(REPO_ROOT)
            parts = rel.parts
            # Only top-level .md files OR .md inside allowed subdirs.
            if len(parts) > 1 and parts[0] not in allowed_dirs:
                continue
            try:
                text = md.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if any(c in text for c in "┌┐└┘─│├┤┬┴┼╔╗╚╝═║"):
                offenders.append(str(rel))
    assert not offenders, f"ASCII art found in: {offenders}"


def test_no_secrets_in_env_example() -> None:
    """``.env.example`` must not contain real secrets."""
    env = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    forbidden = ["sk-live", "sk_test_", "AKIA", "BEGIN PRIVATE KEY"]
    for needle in forbidden:
        assert needle not in env, f"possible secret in .env.example: {needle}"