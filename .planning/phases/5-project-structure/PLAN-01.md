# Phase 5: Project Structure

## Phase Goal
Establish the directory layout, module boundaries, and file organization. Single-language full-stack means a clean separation between the application plane, the worker plane, the data plane, and the infrastructure plane — without the cross-language complexity that a Node+Python split would introduce.

## Top-level layout

```
.
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app factory
│   ├── settings.py                # Pydantic-settings typed config
│   ├── api/                       # HTTP routers
│   │   ├── __init__.py
│   │   ├── auth.py                # /auth/* (SSO login + callback + me)
│   │   ├── templates.py           # /api/templates/*
│   │   ├── ingest.py              # /api/ingest/*
│   │   ├── suggestions.py         # /api/suggestions/*
│   │   ├── review.py              # /api/review/*
│   │   └── admin.py               # /api/admin/* (users, roles, audit)
│   ├── orchestrator/              # Business logic
│   │   ├── __init__.py
│   │   ├── ingest.py              # Pipeline: extract→validate→clean→persist
│   │   ├── templates.py           # Template registry + activation
│   │   ├── suggestions.py         # Rule-based + LLM engine
│   │   ├── review.py              # Approval queue
│   │   ├── audit.py               # Audit log writer
│   │   ├── identity.py            # SSO + RBAC resolution
│   │   └── workers.py             # arq background jobs
│   ├── models/                    # SQLAlchemy ORM
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── ingested_row.py
│   │   ├── template.py
│   │   ├── suggestion.py
│   │   ├── audit_log.py
│   │   └── session.py
│   ├── llm/                       # LLM provider abstraction
│   │   ├── __init__.py
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   └── prompts.py             # Versioned prompt templates
│   ├── ui/                        # Admin UI
│   │   ├── __init__.py
│   │   ├── admin.py               # FastAPI router for /admin/*
│   │   ├── templates/
│   │   │   ├── base.html          # Sidebar layout
│   │   │   ├── dashboard.html
│   │   │   ├── templates.html
│   │   │   ├── ingest.html
│   │   │   ├── review.html
│   │   │   ├── audit.html
│   │   │   └── users.html
│   │   └── static/
│   │       └── admin.css
│   ├── observability/             # Logging + metrics
│   │   ├── __init__.py
│   │   ├── logging.py             # Structured JSON logs
│   │   ├── metrics.py             # Prometheus counters
│   │   └── request_id.py          # Correlation middleware
│   └── db/                        # Database plumbing
│       ├── __init__.py
│       └── migrations/
│           ├── 001_initial.sql
│           └── ...
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_ingest.py
│   ├── test_templates.py
│   ├── test_suggestions.py
│   ├── test_review.py
│   ├── test_audit.py
│   └── test_api.py
├── scripts/
│   ├── verify_stack.py            # Smoke-test all imports
│   ├── seed_dev.py                # Seed dev DB with sample data
│   └── start_workers.sh
├── docs/
│   ├── architecture.svg
│   ├── data-flow.svg
│   └── deployment.md
├── diagrams/                      # SVG diagrams
│   ├── architecture.svg
│   ├── data-flow.svg
│   └── data-model.svg
├── pyproject.toml
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── Dockerfile
└── README.md
```

## Module boundaries

| Layer | Imports from | Does NOT import from |
|-------|--------------|----------------------|
| `app/api/*` | `app/orchestrator/*`, `app/models/*` | `app/db/*` directly, `app/ui/*` |
| `app/orchestrator/*` | `app/models/*`, `app/llm/*` | `app/api/*`, `app/ui/*` |
| `app/models/*` | stdlib + sqlalchemy only | anything else |
| `app/llm/*` | stdlib + provider SDKs | `app/orchestrator/*` |
| `app/ui/*` | `app/api/*` (via HTTP) | `app/orchestrator/*`, `app/models/*` |
| `app/observability/*` | stdlib | `app/orchestrator/*` (cycles!) |

A CI lint enforces these rules: it parses each file's imports and fails the build if a forbidden edge is detected.

## Files to Create

```file:app/__init__.py
"""Automation platform package. Empty by design — subpackages own their exports."""
```

```file:app/api/__init__.py
"""HTTP API package — composes the four resource routers + admin."""
```

```file:app/orchestrator/__init__.py
"""Orchestrator package — wires data ingest → templates → suggestion → review → audit."""
```

```file:app/ui/__init__.py
"""Admin UI package — server-side rendered admin pages + minimal React for the review queue."""
```

```file:app/observability/__init__.py
"""Observability package — structured logging, request-id middleware, metrics."""
```

```file:scripts/__init__.py
"""Scripts package — make verify_stack, seed_dev, start_workers importable for testing."""
```

```file:tests/__init__.py
"""Tests package marker."""
```

## Configuration files

```file:pyproject.toml
[project]
name = "automation-platform"
version = "0.1.0"
description = "Internal automation platform with SSO, RBAC, and audit logging"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "authlib>=1.3.2",
    "python-saml>=1.16.0",
    "httpx>=0.28.0",
    "redis>=5.2.0",
    "arq>=0.26.0",
    "structlog>=24.4.0",
    "sentry-sdk[fastapi]>=2.17.0",
    "openai>=1.54.0",
    "anthropic>=0.39.0",
    "psycopg2-binary>=2.9.9",  # for Alembic migrations
    "jinja2>=3.1.4",
    "python-multipart>=0.0.17",
    "cryptography>=43.0.0",
    "itsdangerous>=2.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "pre-commit>=4.0.0",
    "freezegun>=1.5.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra -q --strict-markers"
```

```file:docker-compose.yml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-automation}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-automation}
      POSTGRES_DB: ${POSTGRES_DB:-automation}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U automation"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "${REDIS_PORT:-6379}:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://automation:automation@postgres:5432/automation
      REDIS_URL: redis://redis:6379/0
    ports:
      - "${API_PORT:-8000}:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app

  worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: arq app.orchestrator.workers.settings
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://automation:automation@postgres:5432/automation
      REDIS_URL: redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app

volumes:
  postgres_data:
```

```file:Dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps for cryptography, python-saml, asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```file:.env.example
# Database
DATABASE_URL=postgresql+asyncpg://automation:automation@localhost:5432/automation

# Redis
REDIS_URL=redis://localhost:6379/0

# SSO — choose ONE
# Azure AD
AZURE_AD_TENANT_ID=
AZURE_AD_CLIENT_ID=
AZURE_AD_CLIENT_SECRET=
# Google Workspace
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
# SAML (Okta, OneLogin, ADFS)
SAML_IDP_METADATA_URL=
SAML_SP_ENTITY_ID=
SAML_SP_ACS_URL=

# Session encryption (Fernet key)
SESSION_SECRET=

# LLM providers (optional — for the suggestion engine)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Logging
LOG_LEVEL=INFO

# Environment
ENVIRONMENT=development
```

## Build & deploy

```file:scripts/verify_stack.py
"""Imports every component and prints 'Stack: N/N components importable'.

Mirrors the pattern from Job-127 — single source of truth for whether
the project will boot.
"""
```

```file:scripts/seed_dev.py
"""Seed dev DB with: 1 admin user, 1 template, 5 ingested rows."""
```

```file:scripts/start_workers.sh
#!/bin/bash
set -e
exec arq app.orchestrator.workers.settings
```

## What this plan does NOT cover

- **CI/CD config** (`.github/workflows/`) — out of scope; we run lint
  + tests locally pre-commit.
- **Frontend SPA build pipeline** — the React bits are bundled with
  Vite into a single static JS file; no webpack/babel config needed.
- **Kubernetes manifests** — single VPS via Docker Compose is the
  deployment target for the MVP.