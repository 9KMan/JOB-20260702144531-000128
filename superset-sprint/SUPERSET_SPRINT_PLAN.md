# Superset Multi-Tenant Sprint Plan
## Docker Compose · Row-Level Security · Embedded Analytics · Highcharts

---

## Objective

Build a production-grade Superset multi-tenant BI platform in **5 days**, covering:
- Containerized local development with Docker Compose
- Row-Level Security (RLS) for tenant isolation
- Embedded analytics (iframe / standalone mode)
- Highcharts visualization integration

---

## Deliverables

| Day | Focus | Key Outputs |
|-----|-------|-------------|
| 1 | Local Superset with Docker Compose | `docker-compose.yml`, init DB, admin user |
| 2 | Multi-tenant dataset modeling | Tenant-aware DB schema, test datasets |
| 3 | Row-Level Security policies | RLS rules per tenant, test queries |
| 4 | Embedded analytics setup | Embedded SDK config, iframe embeds, token auth |
| 5 | Highcharts integration + hardening | Custom Highcharts viz plugin, Prometheus monitoring, production compose |

---

## Tech Stack

| Component | Version/Notes |
|-----------|---------------|
| Apache Superset | 4.x (latest stable) |
| Database (metadata) | PostgreSQL 16 |
| In-memory analytics DB | Apache Druid (optional) or SQLite for dev |
| Container platform | Docker Compose v2 |
| Highcharts | Highcharts JS 11+ (via custom viz plugin) |
| Embedding | Superset Embedded SDK (JavaScript) |
| Auth | Flask AppBuilder (FAB) + JWT for embedding |
| Monitoring | Prometheus + Grafana |

---

## Prerequisites

- Docker Desktop 4.x+ / Docker Engine 24+
- 8 GB RAM minimum (16 GB recommended)
- Python 3.11+ (for custom plugin dev)
- Node.js 18+ (for embedding SDK)
- Git

---

## Tenant Model

```
Organization
  └── Tenant (org_id)
        └── Departments (dept_id)
              └── Users (user_id)
                    └── Role → RLS Policy
```

**RLS enforces**: tenant sees only their own data. Admins see all.

