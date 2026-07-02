# RESEARCH.md

## Tech Stack Decisions

### Backend Framework
**FastAPI** chosen because async-first design handles concurrent automation workflows efficiently, automatic OpenAPI documentation aids integration, and Pydantic provides native validation without additional boilerplate.

### Database
**PostgreSQL 15+** chosen because robust JSONB support enables flexible schema evolution for automation configs, mature row-level security enables multi-tenant isolation, and excellent tooling ecosystem (pgAdmin, pgBouncer) supports production operations.

### ORM / Query Builder
**SQLAlchemy 2.0 (async)** chosen because async driver compatibility enables non-blocking I/O, hybrid attributes support business logic in models, and Alembic provides reliable migrations with branching support.

### API Validation
**Pydantic v2** chosen because native support for discriminated unions handles polymorphic automation payloads, validator decorators maintain clean domain rules, and computed fields reduce redundancy in response models.

### Background Jobs
**Celery + Redis** chosen because mature task tracking enables idempotency guarantees critical for automation retries, flower dashboard provides operational visibility, and result backends persist execution history.

### Authentication
**Authlib + JWT (PyJWT)** chosen because OAuth2 client credentials flow supports service-to-service automation, stateless tokens reduce database lookups, and built-in expiration supports short-lived automation tokens.

### Caching
**Redis 7+** chosen because Lua scripting enables atomic operations for rate limiting, pub/sub supports real-time automation notifications, and stream support enables job queue fallback.

### Testing
**pytest + pytest-asyncio + Factory Boy** chosen because async fixture support matches FastAPI patterns, factory Faker integration enables realistic test data, and parametrize enables comprehensive edge case coverage.

---

## Library Choices

### Web Framework
```
fastapi>=0.109.0,<0.111.0
uvicorn[standard]>=0.27.0,<0.29.0
python-multipart>=0.0.9
```

### Database
```
asyncpg>=0.29.0,<0.30.0
sqlalchemy[asyncio]>=2.0.25,<2.1.0
alembic>=1.13.0,<1.14.0
greenlet>=3.0.0
```

### Validation & Serialization
```
pydantic>=2.6.0,<3.0.0
pydantic-settings>=2.1.0,<3.0.0
email-validator>=2.1.0,<3.0.0
```

### Authentication
```
python-jose[cryptography]>=3.3.0,<4.0.0
passlib[bcrypt]>=1.7.4
authlib>=1.3.0,<2.0.0
```

### Background Jobs
```
celery>=5.3.0,<6.0.0
redis>=5.0.0,<6.0.0
flower>=2.0.0
```

### Utilities
```
httpx>=0.26.0,<0.27.0
python-dateutil>=2.8.0
structlog>=24.0.0
```

### Testing
```
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
factory-boy>=3.3.0
faker>=22.0.0
httpx>=0.26.0
```

---

## Patterns to Use

### 1. Repository Pattern with Unit of Work
Each database operation wraps in a transaction context manager. Aggregates load related entities through repository methods, modifications persist atomically. This isolates ORM coupling and enables unit testing with in-memory stubs.

### 2. Dependency Injection via FastAPI's `Depends()`
Authentication, database sessions, and service layer instances injected as function parameters. Overrides in tests swap real implementations for mocks without modifying application code.

### 3. Domain Event-Driven Workflow Orchestration
Automation steps publish events to internal queue (Celery), downstream handlers consume and execute. Completed steps emit events triggering subsequent steps. This decouples workflow stages and enables transactional outbox pattern for reliability.

### 4. Policy-Based RBAC with Claims
Permissions defined as code objects (not strings), composed into roles. JWT claims encode role identifiers; middleware validates against policy registry. Adding new permissions requires no schema migrations.

### 5. CQRS-Adjacent Read/Write Separation
Write operations use transactional models; read operations query denormalized projection tables updated via triggers or event handlers. Automation dashboard queries never block write throughput.

---

## Trade-offs Considered

### Trade-off 1: Celery vs. Temporal vs. Simple Polling

| Option | Pros | Cons |
|--------|------|------|
| **Celery + Redis** | Mature, familiar, low operational overhead | Limited visibility into complex workflows, manual retry orchestration |
| **Temporal** | Built-in workflow state, saga support, excellent debugging | Steeper learning curve, requires Temporal server deployment |
| **Database polling** | No additional infrastructure | Inefficient, race conditions under load |

**Decision: Celery + Redis**
Rationale: Internal automation workflows rarely require saga patterns or long-running compensations. Celery's operational simplicity outweighs Temporal's capabilities for <30hr/week engagement. Redis already serves caching, minimizing new infrastructure.

### Trade-off 2: Full SQLAlchemy ORM vs. Raw SQL vs. SQLModel

| Option | Pros | Cons |
|--------|------|------|
| **Full SQLAlchemy** | Complete abstraction, migrations, async support | Verbose for simple queries |
| **Raw SQL (asyncpg)** | Maximum performance, precise control | Manual mapping, string-based queries prone to errors |
| **SQLModel** | Pydantic + SQLAlchemy unification | Limited async support, younger ecosystem |

**Decision: SQLAlchemy 2.0 (async) with Core for complex queries**
Rationale: Hybrid approach uses ORM for CRUD and business logic, drops to `text()` or Core for reporting queries. Asyncpg provides driver-level performance where needed.

### Trade-off 3: Monolithic FastAPI vs. Modular Project Structure

| Option | Pros | Cons |
|--------|------|------|
| **Monolithic FastAPI** | Single deployable, simpler routing | Growing coupling over time |
| **Modular with clear boundaries** | Independent service scaling, team separation | Multiple deployables, inter-service communication overhead |

**Decision: Modular monolith with clear domain boundaries**
Rationale: Internal automation platform benefits from single deployment simplicity while maintaining domain separation for future extraction. Feature flags enable gradual service isolation if needed.

---

## Confidence Assessment

| Component | Decision | Confidence | Rationale |
|-----------|----------|------------|-----------|
| FastAPI for API layer | ✅ Adopt | **HIGH** | Battle-tested at scale, async native, excellent docs |
| PostgreSQL for persistence | ✅ Adopt | **HIGH** | Proven for automation workloads, JSONB flexibility |
| SQLAlchemy 2.0 async | ✅ Adopt | **HIGH** | Stable release, comprehensive async support |
| Pydantic v2 for validation | ✅ Adopt | **HIGH** | Major improvement over v1, active development |
| Celery + Redis for jobs | ✅ Adopt | **MEDIUM** | Proven but complexity grows; accept tradeoff for simplicity |
| JWT for auth tokens | ✅ Adopt | **HIGH** | Standard practice, stateless validation |
| Repository + Unit of Work | ✅ Adopt | **HIGH** | Well-understood pattern, testable |
| Dependency injection via Depends | ✅ Adopt | **HIGH** | Native FastAPI pattern, minimal magic |
| Celery over Temporal | ✅ Adopt | **MEDIUM** | Trade-off accepted for operational simplicity |
| Modular monolith structure | ✅ Adopt | **MEDIUM** | Appropriate for project scope; revisitable |