# Phase 6: Out-of-Scope

## Phase Goal
Explicitly enumerate what this build does NOT include. The buyer asked for "internal automation" without specifying scope — this section draws the line so we don't get pulled into a never-ending scope-creep engagement.

## Sections (mandatory format)

### Out-of-Scope Workstreams

| # | Workstream | Why deferred |
|---|------------|--------------|
| 1 | **Multi-tenant SaaS** | Internal tool only; single org, single DB. Multi-tenancy would add tenant_id to every row + RLS policies. Future phase if you productize. |
| 2 | **Mobile clients** | Web-responsive admin UI covers the operator use case. A native mobile app would add a second deploy pipeline (iOS + Android) without a concrete user need. |
| 3 | **End-user-facing chat UI** | Internal tool; users are operators + reviewers, not customers. A customer-facing chat would be a separate product. |
| 4 | **Model fine-tuning** | The suggestion engine uses off-the-shelf OpenAI/Anthropic. Fine-tuning a model for your specific domain is a 4-6 week engagement on its own. |
| 5 | **Voice / speech-to-text** | Not requested. The data ingest path is text + structured data only. Add a transcription service if needed. |
| 6 | **Computer vision / image ingest** | Not requested. If you need OCR on PDFs, that's a separate pipeline. |
| 7 | **Video processing** | Not requested. |
| 8 | **Robotic process automation (RPA)** | This is software automation, not UI-bots-clicking-buttons. Different stack entirely (UiPath, Automation Anywhere). |
| 9 | **Blockchain / on-chain settlement** | Not requested; out of band for an internal automation tool. |
| 10 | **HIPAA certification** | The platform can be configured to handle PHI (encryption at rest, audit log, RBAC), but we are not building it as a HIPAA-compliant product out of the gate. |
| 11 | **FedRAMP authorization** | Same — the architecture supports it, but the certification process is 12-18 months on its own. |
| 12 | **PCI-DSS certification** | Same — if you process payment data, the platform can host it with the right controls, but we don't ship a PCI-certified product. |
| 13 | **SOC 2 Type II audit** | Same — we can give you the architecture to pass an audit, but the audit itself is out of scope. |
| 14 | **Customer-facing billing / invoicing** | This is an internal tool, not a billed product. |
| 15 | **Public-facing marketing site** | Not requested. |
| 16 | **Real-time collaborative editing** | The template editor is single-user-with-versioning. No Google-Docs-style multi-cursor. |
| 17 | **Custom SSO IdP integration (beyond OIDC + SAML)** | OIDC + SAML covers ~99% of enterprise IdPs. If you have something exotic (custom Kerberos, LDAP-only, etc.), that's a separate engagement. |
| 18 | **End-user onboarding flows** | Internal tool; onboarding is "ask your manager for an invite." |
| 19 | **Webhooks to external systems** | The data pipeline pulls from external sources; it doesn't push to them. Adding outbound webhooks is a future feature. |
| 20 | **Custom report builder** | The dashboard is opinionated. Power users get SQL access to the read replica. |

### Integration Boundaries

| Boundary | What's in scope | What's out |
|----------|-----------------|------------|
| **SSO providers** | Azure AD, Google Workspace, Okta, OneLogin, any OIDC-compliant IdP, any SAML 2.0 IdP | Custom enterprise IdPs that don't speak OIDC or SAML |
| **Source systems (ingest)** | CSV upload, REST webhook, SFTP drop, Postgres CDC, scheduled HTTP fetch | Kafka, Kinesis, Pulsar (message-bus-first ingest) |
| **LLM providers** | OpenAI, Anthropic | Self-hosted models, Cohere, AI21, etc. |
| **Databases** | PostgreSQL 16 with pgvector | MySQL, MongoDB, DynamoDB |
| **Deployment** | Single VPS via Docker Compose, or your AWS/GCP/Azure account with docker-compose up | Kubernetes (separate engagement), bare-metal, serverless |
| **Observability** | Structured JSON logs + Sentry + Prometheus | Datadog, New Relic, Honeycomb (can integrate but not ship with) |

### Explicit Non-Goals

1. **This is not a no-code platform.** Templates are JSON; users comfortable with JSON edit them. If you need a no-code visual editor, that's a different product.
2. **This is not a low-code platform.** It requires a Python engineer to deploy and maintain.
3. **This is not a chatbot.** There's no conversational interface. The UI is operator-focused: dashboards, tables, review queues.
4. **This is not a CRM.** It can integrate with a CRM via API, but it's not one.
5. **This is not a data warehouse.** We use Postgres for transactional storage + vector search, not for analytical workloads at >10TB scale.
6. **This is not a workflow engine.** There's no BPMN, no visual flowchart editor. Workflows are Python functions.
7. **This is not a real-time system.** Latency budgets are seconds-to-minutes, not milliseconds.
8. **This is not a public API.** The HTTP surface is for the admin UI and operator scripts; rate limits are tight; no public docs.

### Deferred Phases (post-MVP roadmap)

| Phase | Trigger | Scope |
|-------|---------|-------|
| **Phase 2: Scale** | >10K ingested rows/day OR >50 concurrent operators | Add read replicas, partitioning, Redis caching, Kafka for ingest |
| **Phase 3: AI features** | Customer asks for semantic search | Add pgvector-based "find similar rows" + similarity-clustered review queue |
| **Phase 4: External APIs** | Customer wants to expose data to partners | Add API gateway, OAuth2 for partners, rate limiting per tenant |
| **Phase 5: Multi-tenant** | Productizing the tool for resale | Add tenant_id to every row, RLS policies, per-tenant SSO config |
| **Phase 6: Compliance** | Customer requires SOC 2 / HIPAA | Add compliance logging, encryption-at-rest, BAA-grade audit retention |

### Reference table — JD requirement → where it lives

| JD requirement | In-scope file/component |
|----------------|-------------------------|
| Raw data ingest | `app/orchestrator/ingest.py` |
| Data cleaning | `app/orchestrator/ingest.py::clean()` |
| Templates | `app/orchestrator/templates.py` |
| Suggestion generation | `app/orchestrator/suggestions.py` |
| Database | `app/models/*` + `app/db/migrations/001_initial.sql` |
| User login (SSO) | `app/orchestrator/identity.py` |
| RBAC | `app/models/role.py` + `app/api/admin.py` |
| Review workflows | `app/orchestrator/review.py` + `app/ui/templates/review.html` |
| History logging | `app/orchestrator/audit.py` + `app/models/audit_log.py` |
| Frontend | `app/ui/templates/*` + `app/ui/static/admin.css` |
| Backend | `app/api/*` + `app/orchestrator/*` |

## What "done" looks like

The MVP is shipped when:

1. An admin can sign in via SSO and reach the dashboard in <10 seconds.
2. An admin can upload a CSV; the platform ingests, cleans, and runs it through an active template.
3. The suggestion engine produces draft Suggestions from cleaned rows.
4. Operators see Suggestions in the review queue, approve/reject/edit them.
5. Every action is in the audit log.
6. New templates can be created in the UI without a deploy.
7. Tests pass (`pytest`), stack imports cleanly (`scripts/verify_stack.py`), the app boots (`uvicorn app.main:app`).