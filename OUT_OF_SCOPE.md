# OUT_OF_SCOPE — Internal Automation Platform

This document enumerates features that were **deliberately** excluded
from this build.  Every entry below is paired with a code reference
that demonstrates the deferment — typically a `NotImplementedError`
subclass or a `pass`-only stub.

> **Process:**  When a future sprint adds an OUT_OF_SCOPE item, it
> must (a) add a new section here, (b) add the corresponding code
> marker, and (c) update `tests/test_out_of_scope_doc.py` if the
> shape of the marker changes.

---

## Advanced ML-based confidence scoring

The current `score_confidence` implementation is a simple arithmetic
mean over per-rule scores.  An LLM-based or gradient-boosted scorer
would give materially better calibration, but it requires (a) a
training corpus we do not yet have and (b) infra for model serving
that is out of budget for v1.

**Code reference:** `app/orchestrator/suggestions.advanced_ml_scorer`
raises `NotImplementedInScopeError` if called.

---

## Real SSO token validation

The `get_current_user` dependency in `app/dependencies.py` accepts
no real token — it only honours the `dev_bypass_auth` setting.  Wiring
up a real OIDC / SAML flow is deferred until the corporate SSO
provider is selected.

**Code reference:** `app/dependencies.get_current_user` returns
`401` for any non-bypass request.

---

## Webhook ingestion

External systems can push data into the platform via the ingestion
pipeline, but only as pull (CSV uploads + scheduled DB replicas).
Webhook receivers (Slack-style push URLs) are intentionally not in
v1 — they expand the attack surface and require a public ingress
that the security review has not yet approved.

**Code reference:** No `app/api/webhooks.py` module exists.

---

## UI beyond the API

This repo ships the API and the orchestration engine only.  The
human-facing review UI is a separate repository and ships in a later
iteration.

**Code reference:** `app/ui/__init__.py` is a placeholder.

---

## OpenTelemetry exporter to a remote collector

The tracing setup in `app/observability/tracing.py` only emits to
stdout (via `ConsoleSpanExporter`).  Sending spans to a real
collector (Tempo / Jaeger / Honeycomb) is deferred until the SRE
team confirms which backend to standardise on.

**Code reference:** `app.observability.tracing.configure_tracing`
silently no-ops if the OpenTelemetry deps are not installed.

---

## Multi-tenant isolation

A single instance currently serves one tenant.  Row-level security
policies, tenant-aware connection routing, and per-tenant secrets
are out of scope for v1.

**Code reference:** No `tenant_id` column on any domain table.