# Superset Row-Level Security Policies (RLSPAC)

## The Access Model

| User | Role | Sees |
|------|------|------|
| Alice (CEO) | executive | ALL data for Acme Corp |
| Bob (Sales Mgr) | manager | Sales business_unit ONLY for Acme Corp |
| Carol (Analyst) | analyst | Sales business_unit for Acme Corp |
| Dan (Founder) | executive | ALL data for TechStart |
| Eve (Developer) | analyst | Engineering business_unit ONLY for TechStart |

## How Superset RLS Works

1. Superset stores RLS policies in `溪: Security > Row Level Security`
2. Each policy has:
   - `name`: descriptive name
   - `filter_type`: `Base` (SQL) or `Regular Expression`
   - `clause`: SQL WHERE clause (uses Jinja `{{}}` for dynamic values)
   - `roles`: which Superset roles this applies to
   - `databases`: which DBs

3. Jinja variables available:
   - `{{ URL_Param("key") }}` — URL parameter
   - `{{ FORM_DATA }` — submitted form data
   - `{{ ANNOTATION_JOB }` — annotation data
   - `{{ get_user_id() }}` — current user ID
   - `{{ get_username() }}` — current username

## RLS Policies for Multi-tenant SaaS

### Policy 1: Executive — sees all their company's data
```json
{
  "name": "Executive: See All Company Data",
  "filter_type": "Base",
  "clause": "company_id = {{ TAG.tenant_id }}",
  "roles": ["Executive"],
  "databases": ["mariadb"]
}
```

### Policy 2: Manager/Analyst — sees only their business unit
```json
{
  "name": "Manager: See Business Unit Only",
  "filter_type": "Base",
  "clause": "company_id = {{ TAG.tenant_id }} AND business_unit = {{ TAG.business_unit }}",
  "roles": ["Manager", "Analyst"],
  "databases": ["mariadb"]
}
```

## Implementation Steps in Superset UI

1. **Connect Superset to MariaDB**
   - Sources > Databases > + Add Database
   - SQLAlchemy URI: `mysql+pymysql://root:root_secret@mariadb:3306/multitenant_saas`

2. **Connect the dataset**
   - Sources > Databases > [mulitenant_saas] > Edit > Tables > + Add Table
   - Add: `sales`, `users`, `companies`

3. **Create database roles per tenant**
   ```sql
   -- Role for Acme Corp
   CREATE ROLE 'acme_readonly';
   GRANT SELECT ON multitenant_saas.sales TO 'acme_readonly';
   GRANT SELECT ON multitenant_saas.users TO 'acme_readonly';
   
   -- Role for TechStart
   CREATE ROLE 'techstart_readonly';
   GRANT SELECT ON multitenant_saas.sales TO 'techstart_readonly';
   GRANT SELECT ON multitenant_saas.users TO 'techstart_readonly';
   ```

4. **Tag users with tenant_id**
   - Add custom field or use Superset's `TAG` system
   - Map: `TAG.tenant_id = 1` for Acme, `TAG.tenant_id = 2` for TechStart

5. **Create Superset roles**
   - Security > List Roles > +
   - Role name: `Executive_Acme`, `Manager_Acme`, etc.
   - Assign database roles

6. **Create RLS policies**
   - Security > Row Level Security >
   - + Add Filter
   - Apply the clauses above to the relevant roles

## Testing RLS

```sql
-- As Executive (Acme): should see ALL 6 rows
SELECT * FROM sales WHERE company_id = 1;

-- As Manager (Acme, Sales): should see only 3 rows
SELECT * FROM sales WHERE company_id = 1 AND business_unit = 'Sales';

-- As TechStart Executive: should see all 4 rows
SELECT * FROM sales WHERE company_id = 2;

-- As TechStart Analyst (Engineering): should see only 2 rows
SELECT * FROM sales WHERE company_id = 2 AND business_unit = 'Engineering';
```

## Key Superset Config for RLS

In `superset_config.py`:
```python
ROW_LEVEL_SECURITY_ENABLED = True
ENABLE_RLS = True

# Tag-based tenancy (Superset 3.0+)
TAG_REGISTRY = {
    "tenant_id": {
        "acme": 1,
        "techstart": 2,
    }
}
```
