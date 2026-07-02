# Phase 4: Data Model

## Phase Goal
Define the data model — the 8 tables that the platform needs to operate: users (mapped from IdP), roles, ingested rows, templates (versioned), suggestions, review queue, audit log, and the SSO session store.

All tables use:
- UUID primary keys (server-side `gen_random_uuid()`)
- `created_at` / `updated_at` with timezone=True
- Where applicable: `JSONB` for flexible payloads
- Where applicable: `vector(1536)` for semantic search over ingested rows

## Files to Create

```file:app/models/__init__.py
"""SQLAlchemy ORM models. Re-exports for `from app.models import ...`."""
```

```file:app/models/base.py
"""Declarative base + timestamp + UUID mixins. Mirrors Job-127 base."""
```

```file:app/models/user.py
"""User — mapped from SSO IdP. The IdP is the source of truth.

Schema:
- id (UUID PK)
- email (unique, indexed)
- sso_provider (azure_ad | google | saml_okta | ...)
- sso_subject (the IdP's stable user id)
- display_name
- role_id (FK to roles)
- is_active
- last_login_at
- created_at, updated_at

We NEVER store passwords. Login goes through the IdP.
"""
```

```file:app/models/role.py
"""Role — RBAC role with granular permissions.

Schema:
- id (UUID PK)
- name (unique, e.g. 'admin', 'operator', 'viewer')
- description
- permissions (JSONB list of ``{resource, action}`` pairs)
- is_system (true for built-in roles, false for custom)
- created_at, updated_at

Built-in roles:
- ``admin`` — full access (template edit, user mgmt, audit view)
- ``operator`` — review queue, suggestion approval, ingest run trigger
- ``viewer`` — read-only on dashboards + audit
"""
```

```file:app/models/ingested_row.py
"""IngestedRow — one row of raw + cleaned data after pipeline runs.

Schema:
- id (UUID PK)
- source_id (string — adapter name like 'csv_upload_42' or 'webhook_xyz')
- source_row_hash (unique with source_id, deterministic dedup)
- raw_payload (JSONB)
- cleaned_payload (JSONB)
- template_id (FK to templates)
- template_version_id (FK to template_versions)
- status (pending | cleaned | suggested | failed)
- error_message (text)
- ingested_at, processed_at
- created_at, updated_at

The (source_id, source_row_hash) unique index makes ingest idempotent.
"""
```

```file:app/models/template.py
"""Template — versioned rule set for processing ingested rows.

Two tables:

``templates``:
- id (UUID PK)
- key (unique, e.g. 'customer_record_default')
- name, description
- created_by (FK to users)
- created_at, updated_at

``template_versions``:
- id (UUID PK)
- template_id (FK)
- version (int, monotonically increasing per template)
- status (draft | active | archived)
- rules (JSONB — field mappings, transformations, regex, etc.)
- prompt (text — for LLM fallback)
- activated_at, activated_by
- created_at, updated_at

Constraint: only one ``active`` version per ``template_id``.
"""
```

```file:app/models/suggestion.py
"""Suggestion — a draft edit/decision produced by the suggestion engine.

Schema:
- id (UUID PK)
- ingested_row_id (FK)
- template_version_id (FK)
- output_payload (JSONB)
- confidence (float 0-1)
- source (rule | llm | hybrid)
- status (pending | approved | rejected | applied)
- reviewer_id (FK to users, nullable)
- reviewed_at (timestamp, nullable)
- review_note (text, nullable)
- applied_at (timestamp, nullable)
- created_at, updated_at
"""
```

```file:app/models/audit_log.py
"""AuditLog — append-only event store.

Schema:
- id (UUID PK)
- timestamp (with timezone, indexed)
- user_id (FK to users, nullable for system events)
- user_email (denormalized, in case user is later deleted)
- action (string, e.g. 'template.activate', 'suggestion.approve')
- resource_type (string)
- resource_id (string, indexed)
- status (success | failure)
- ip_address, user_agent, request_method, request_path
- before_state (JSONB, nullable)
- after_state (JSONB, nullable)
- request_id (UUID, indexed — for log correlation)
- metadata (JSONB, additional context)

DB-level enforcement:
- REVOKE UPDATE, DELETE ON audit_logs FROM app_user
- Only the ``audit_writer`` role can INSERT.
"""
```

```file:app/models/session.py
"""SSOSession — server-side session store for OIDC/SAML logins.

Schema:
- id (UUID PK, the session token)
- user_id (FK to users)
- idp_provider, idp_subject
- id_token (text, encrypted at rest)
- refresh_token (text, encrypted at rest)
- expires_at
- created_at, last_used_at

Tokens are encrypted with Fernet (symmetric, key from settings).
Expired sessions are reaped by a daily cron.
"""
```

```file:db/migrations/001_initial.sql
"""Initial schema migration.

Creates all 8 tables, indexes, and the audit-log permissions:
- CREATE EXTENSION IF NOT EXISTS pgcrypto;
- CREATE EXTENSION IF NOT EXISTS vector;
- (table definitions)
- REVOKE UPDATE, DELETE ON audit_logs FROM app_user;
- GRANT INSERT ON audit_logs TO audit_writer;

Idempotent (uses IF NOT EXISTS where supported).
"""
```

## Entity-relationship overview

```
users ─┬─< role (many-to-one)
       └─< audit_logs
       └─< sso_sessions

templates ─< template_versions ─< ingested_rows ─< suggestions
                                                  │
                                                  └─< audit_logs
```

## Indexing strategy

| Table | Index | Reason |
|-------|-------|--------|
| users | (email) unique | SSO login lookup |
| users | (sso_provider, sso_subject) unique | IdP cross-ref |
| ingested_rows | (source_id, source_row_hash) unique | Idempotent ingest |
| ingested_rows | (status) | Worker queue scan |
| ingested_rows | (template_id, status) | Per-template worker batching |
| template_versions | (template_id, status) | Find active version |
| suggestions | (status, confidence DESC) | Review queue ordering |
| audit_logs | (timestamp DESC) | Time-range queries |
| audit_logs | (user_id, timestamp DESC) | Per-user history |
| audit_logs | (resource_type, resource_id) | Resource history |

## Migration policy

- All migrations are forward-only. Never edit a migration that's been
  applied; write a new one.
- Migrations run inside a transaction. If any DDL fails, the entire
  migration rolls back.
- The audit_log table has NO migration that drops data — it grows
  forever, and we use a separate compaction job (see workers.py in
  Phase 3) to roll up old rows into monthly aggregates.