# Row-Level Security (RLS) Implementation Guide

## Overview

Superset implements RLS through **Security > Row Level Security** with filter conditions
applied to datasets (tables). This enforces tenant isolation at the query level.

## Superset RLS Setup

### 1. Create Base Tables in Superset

1. Navigate to **Sources > Databases > Add Database**
2. Connect to `tenant-db` (PostgreSQL at `tenant-db:5432`)
3. Under **Sources > Tables > Add Table**, add:
   - `public.sales`
   - `public.tenants`
   - `public.users`

### 2. Row Level Security Rules

Navigate: **Security > Row Level Security > +**

#### Rule: Tenant Data Isolation

| Field | Value |
|-------|-------|
| Name | `Tenant Isolation - Sales` |
| Filter Type | `Regular` |
| Base URL | (leave empty) |
| Tables | `sales` |
| Clause | `{{ #if current_user_id }} tenant_id = '{{ current_user_id }}' {{ #endif }}` |

**Note**: Use `filter_values` with a custom filter template or pass `tenant_id` via session context.

#### Recommended Approach: Virtual Datasets with WHERE clause

Create dataset SQL query:
```sql
SELECT id, sale_date, product, amount, quantity, region
FROM sales
WHERE tenant_id = '{{ current_user_tenant_id }}'
```

### 3. Assigning RLS to Roles

1. Create role: **Tenant Admin** (can manage their tenant's data)
2. Create role: **Tenant Viewer** (read-only)
3. Link RLS filter to each role via **Security > Row Level Security > [rule] > Roles**

---

## Alternative: Database-Level RLS (PostgreSQL)

```sql
-- Applied at the PostgreSQL level
ALTER TABLE sales ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON sales
    USING (tenant_id = current_setting('app.current_tenant_id', true));
```

Set tenant context via Superset `pre_query` hook or connection filter.

---

## Testing RLS

```python
# Test query - should return only tenant's data
SELECT * FROM sales WHERE tenant_id = 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33';
```

---

## Common Pitfalls

- **User attribute not set**: Ensure user attributes (`tenant_id`) are set in FAB profile
- **Cache bypass**: RLS is applied at query execution, not caching — use consistent cache keys
- **Admin users**: Admin role bypasses RLS by default. Add explicit filter if admin should also be scoped
