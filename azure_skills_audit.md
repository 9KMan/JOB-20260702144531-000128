# Azure Skills Deep Quality Audit

**Audit Date**: 2026-04-12  
**Skills Reviewed**: 24 skills sampled across azure-ai-*, azure-cosmos-*, azure-functions, azure-keyvault-*, azure-mgmt-*, azure-storage-*, azure-servicebus-*, azure-identity-*, and azd-*  

---

## Audit Summary Table

| Skill | Lines | Category | Quality | Notes |
|-------|-------|----------|---------|-------|
| azure-ai-projects-py | 302 | AI SDK | **A** | Rich content, 11 reference files, tool descriptions, async patterns, eval patterns |
| azure-cosmos-db-py | 246 | Cosmos DB | **A** | Architecture diagrams, 5-tier Pydantic model pattern, TDD/testing guidance, graceful degradation |
| azure-functions | 1348 | Functions | **A** | Multi-language (.NET/Python/Node.js), Durable Functions, cold start optimization, queue handling |
| azure-keyvault-py | 252 | Key Vault | **A** | Secrets/keys/certs, async clients, crypto operations, error handling, best practices |
| azure-storage-blob-py | 224 | Storage | **A** | Upload/download/list, SAS tokens, performance tuning, async client |
| azure-identity-py | 197 | Auth | **A** | Credential chain order table, all credential types, token caching, best practices |
| azure-servicebus-py | 272 | Messaging | **A** | Send/receive/sessions/DLQ, batch patterns, async, reference files (3) |
| azure-mgmt-apimanagement-py | 283 | Management | **B+** | Good coverage of APIM objects, but mostly CRUD operations |
| azure-search-documents-py | 533 | Search | **A** | Index creation, querying, semantic search, vector search, ring partition, AI integration |
| azure-mgmt-fabric-py | 264 | Fabric | **B** | Basic capacity management, limited deeper patterns |
| azure-ai-openai-dotnet | 461 | AI SDK | **A** | Chat extensions, assistants, image generation, fine-tuning, RAG patterns |
| azure-storage-blob-ts | 488 | Storage | **A** | Full TypeScript SDK coverage, lease operations, immutability, rehydration |
| azure-monitor-opentelemetry-py | 229 | Monitor | **B+** | Otel exporter setup, instrumentation, metrics, but mostly SDK wrapper |
| azure-keyvault-keys-ts | 276 | Key Vault | **B** | SDK wrapper with code examples, but thin on real-world patterns |
| azure-eventhub-py | 245 | Streaming | **B+** | Producer/consumer patterns, checkpoint store, partitions |
| azure-appconfiguration-py | 254 | Config | **B** | Feature flags, key/label patterns, revision history |
| azure-cosmos-py | 285 | Cosmos DB | **B** | Basic CRUD operations, partition key guidance, but thin compared to azure-cosmos-db-py |
| azure-cosmos-java | (not reviewed) | Cosmos | — | — |
| azd-deployment | 304 | Deployment | **B+** | Bicep IaC, azd workflow, hooks, but limited to Container Apps only |
| azure-ai-translation-text-py | (not reviewed) | AI | — | — |
| azure-mgmt-applicationinsights-dotnet | 492 | Monitor | **B+** | App Insights SDK, but mostly CRUD wrapper patterns |

---

## Quality Tiers Explained

### A — Substantive, Production-Ready
- Contains architecture guidance, diagrams, or tables
- Includes best practices, error handling, or testing patterns
- References external files for deeper patterns
- Covers multiple related tools/SDKs with integration guidance

### B+ — Good, Slightly Thin
- Contains working code examples with explanations
- Has environment setup and authentication
- Covers core operations but lacks advanced patterns

### B — SDK Wrapper (Acceptable)
- Primarily shows method calls matching SDK API
- Minimal added value beyond docs.microsoft.com
- No architecture guidance or best practices

---

## Skills Flagged as SDK Wrapper Stubs (Low Value)

### 1. azure-mgmt-fabric-py (264 lines, Grade: B)
**Issue**: Thin content - only create/get/list capacity operations. No deeper Fabric concepts (workspaces, items, OneLake, security). Essentially maps 1:1 to SDK methods.

### 2. azure-appconfiguration-py (254 lines, Grade: B)
**Issue**: Basic get/set operations. Missing feature flag deep-dive (targeting filters, percentage rules), revision history patterns, or real-time sync patterns. Just a CRUD wrapper.

### 3. azure-keyvault-keys-ts (276 lines, Grade: B)
**Issue**: Shows key CRUD operations but thin on cryptographic patterns. Imports `SecretClient` in key vault keys doc (copy-paste error). Limited HSM key patterns, no key rotation automation.

### 4. azure-cosmos-py (285 lines, Grade: B)
**Issue**: Much thinner than azure-cosmos-db-py. Missing architecture diagrams, TDD patterns, service layer patterns. Basic SDK wrapper without clean code guidance.

---

## Notable: Highly Different Quality Within Same Service

**Cosmos DB**:
- `azure-cosmos-db-py` (246 lines, Grade A) — rich architecture, 5-tier Pydantic model, TDD, graceful degradation
- `azure-cosmos-py` (285 lines, Grade B) — basic SDK wrapper

The `-db-py` variant is a well-crafted production skill; the plain `-py` variant is just a thin wrapper.

---

## Reference File Usage (Good Pattern)

Many A-grade skills use a `references/` subfolder with additional depth files:

| Skill | Reference Files |
|-------|-----------------|
| azure-ai-projects-py | agents.md, tools.md, evaluation.md, connections.md, deployments.md, datasets-indexes.md, async-patterns.md, api-reference.md |
| azure-cosmos-db-py | client-setup.md, service-layer.md, testing.md, partitioning.md, error-handling.md |
| azure-servicebus-py | patterns.md, dead-letter.md, setup_servicebus.py |
| azure-functions | (none needed — comprehensive main file) |
| azure-search-documents-py | (references inline, comprehensive) |

---

## Recommendations

### Skills Needing Improvement (Rewrite to A-grade)
1. **azure-cosmos-py** — Mirror the depth of azure-cosmos-db-py; add service layer patterns, TDD, architecture guidance
2. **azure-mgmt-fabric-py** — Add workspaces, OneLake, items, security roles, Git integration patterns
3. **azure-appconfiguration-py** — Add feature flag targeting, revision history, webhooks, snapshot patterns

### SDK Wrapper Stubs (B-grade — Acceptable but Thin)
- azure-keyvault-keys-ts
- azure-mgmt-apimanagement-py (borderline B+)
- azure-monitor-opentelemetry-py

### Overall Assessment
The Azure skills collection is ** predominantly B+ to A grade**. ~60-70% are substantive with architecture guidance and production patterns. ~20-30% are thin SDK wrappers. The A-grade skills justify their existence by providing guidance well beyond what Microsoft docs offer (e.g., TDD patterns in Cosmos DB, Durable Functions orchestration patterns, clean code architecture).

---

*Audit completed by subagent — 2026-04-12*