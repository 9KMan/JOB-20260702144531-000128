# dbt Skill Guide — Hermes Agent Reference

## Overview

dbt (data build tool) is an analytics engineering tool that transforms data in warehouses using SQL. It implements a **DAG-based** workflow where models reference each other via `ref()`, creating a dependency graph that dbt executes in topological order.

**Key Concept:** dbt is NOT an ETL tool — it reads from your warehouse and writes back to your warehouse. It does not extract or load data; it only transforms.

---

## Core Concepts

### `ref()` vs `source()`

```sql
-- source() - References raw tables defined in schema.yml under sources
-- Use for: Staging models that ingest from external systems
{{ source('ecom', 'orders') }}

-- ref() - References other dbt models (managed by dbt DAG)
-- Use for: Any model that depends on other models
{{ ref('staging_orders') }}
```

**Rule of Thumb:**
- `source()` → Data entering dbt from external systems (raw tables)
- `ref()` → Models you are building within dbt (transformed models)

---

## dbt Commands Reference

### Standard Commands
```bash
dbt run                        # Run all models
dbt test                       # Run all tests
dbt build                      # Run + test + docs (full pipeline)
dbt compile                    # Compile SQL without running
```

### Selection Commands
```bash
dbt run --select my_model                # Run specific model
dbt run --select +my_model                # Run model + upstream dependencies
dbt run --select my_model+                # Run model + downstream dependencies
dbt run --select +my_model+               # Run model + upstream + downstream
dbt run --select tag:finance              # Run models with specific tag
dbt run --exclude my_model                # Exclude specific model
```

### Documentation Commands
```bash
dbt docs generate            # Generate documentation artifacts
dbt docs serve               # Serve docs at http://localhost:8080
```

### Source & Freshness Commands
```bash
dbt source freshness                      # Check if sources are fresh
dbt source freshness --select source:ecom # Check specific source
```

### Other Commands
```bash
dbt debug                    # Verify project configuration
dbt deps                     # Install packages from packages.yml
dbt seed                      # Load CSV files from seeds folder
dbt snapshot                 # Run snapshot models
dbt ls                        # List all resources in project
```

---

## Jinja Macros Reference

### Standard Variables
```sql
{{ this }}                    # Current model (schema.table)
{{ target }}                  # Target profile (target.name, target.database)
{{ run_started_at }}          # Timestamp when run started
```

### Conditionals
```sql
{% if is_incremental() %}
  -- This runs only on incremental runs
  WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```

### Loops
```sql
{% for status in ['pending', 'shipped', 'delivered'] %}
  SUM(CASE WHEN order_status = '{{ status }}' THEN 1 ELSE 0 END) AS {{ status }}_count
{% endfor %}
```

### Macros from dbt_utils
```sql
-- Pivot utility
{{ dbt_utils.pivot(column='status', values=['pending','shipped','delivered']) }}

-- Star pattern (select all columns except)
SELECT {{ dbt_utils.star(from=ref('orders'), except=['password','secret']) }}

-- Surrogate key
{{ dbt_utils.surrogate_key(['customer_id', 'order_date']) }}

-- Date difference
{{ dbt_utils.date_diff('order_date', 'ship_date', 'day') }}
```

### Custom Macro Example
```sql
-- macros/optional_filter.sql
{% macro optional_filter(column_name, operator, value, condition) %}
    {% if condition %}
        {{ column_name }} {{ operator }} {{ value }}
    {% endif %}
{% endmacro %}
```

---

## Project Structure

```
dbt_project/
├── dbt_project.yml          # Project configuration
├── profiles.yml             # Database connections (outside project typically)
├── packages.yml              # External packages (dbt_utils, etc.)
│
├── models/                   # SQL model files
│   └── example/              # Project subfolder
│       ├── schema.yml        # Models config, tests, descriptions
│       ├── staging/          # Staging models (source data)
│       │   └── stg_orders.sql
│       ├── intermediate/     # Intermediate transformations
│       │   └── int_order_items.sql
│       └── marts/            # Final business logic tables
│           ├── fct_orders.sql
│           └── dim_customers.sql
│
├── macros/                   # Reusable Jinja macros
│   └── optional_filter.sql
│
├── snapshots/                # Snapshot models (SCD Type 2)
│   └── scd_customers.sql
│
├── seeds/                     # CSV files loaded as tables
│   └── tax_rates.csv
│
└── tests/                     # Custom singular tests
    └── test_models.sql
```

---

## Adapter Patterns

### PostgreSQL (profiles.yml)
```yaml
default:
  outputs:
    dev:
      type: postgres
      host: localhost
      port: 5432
      user: dbt_user
      password: dbt_password
      dbname: ecommerce
      schema: dbt_dev
      threads: 4
    prod:
      type: postgres
      host: production-db.example.com
      port: 5432
      user: prod_user
      password: "{{ env_var('DBT_PROD_PASSWORD') }}"
      dbname: ecommerce
      schema: dbt_prod
      threads: 8
  target: dev
```

### Snowflake (profiles.yml)
```yaml
default:
  outputs:
    dev:
      type: snowflake
      account: xy12345.us-east-1
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
      role: ANALYTICS_ROLE
      database: ECOMMERCE_DEV
      warehouse: COMPUTE_WH
      schema: DBT_DEV
      threads: 8
    prod:
      type: snowflake
      account: xy12345.us-east-1
      user: "{{ env_var('SNOWFLAKE_PROD_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PROD_PASSWORD') }}"
      role: PROD_ROLE
      database: ECOMMERCE_PROD
      warehouse: PROD_WH
      schema: DBT_PROD
      threads: 16
  target: dev
```

### BigQuery (profiles.yml)
```yaml
default:
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: my-gcp-project
      dataset: ecommerce_dev
      location: US
      keyfile: /path/to/service-account.json
      threads: 8
    prod:
      type: bigquery
      method: service-account
      project: my-gcp-project
      dataset: ecommerce_prod
      location: US
      keyfile: /path/to/service-account.json
      threads: 16
  target: dev
```

---

## Testing Patterns

### Generic Tests (Schema Tests) — defined in schema.yml
```yaml
models:
  - name: dim_customers
    columns:
      - name: customer_id
        tests:
          - unique
          - not_null
      - name: email
        tests:
          - unique
          - not_null
      - name: customer_tier
        tests:
          - accepted_values:
              values: ['bronze', 'silver', 'gold', 'platinum']
      - name: customer_id
        tests:
          - relationships:
              to: ref('stg_customers')
              field: customer_id
```

### Singular Tests — custom SQL validation
```sql
-- tests/check_order_revenue.sql
-- Ensures order revenue matches line item sum
SELECT
    o.order_id,
    o.total_amount,
    SUM(oi.quantity * oi.unit_price) AS line_item_total,
    o.total_amount - SUM(oi.quantity * oi.unit_price) AS discrepancy
FROM {{ ref('fct_orders') }} o
JOIN {{ ref('int_order_items') }} oi ON o.order_id = oi.order_id
GROUP BY o.order_id, o.total_amount
HAVING ABS(o.total_amount - SUM(oi.quantity * oi.unit_price)) > 0.01
```

---

## Materialization Strategies

| Strategy | Use Case | Behavior |
|----------|----------|----------|
| `table` | Small tables, snapshots | Recreates full table each run |
| `view` | Large tables, frequently accessed | Creates SQL view (no data stored) |
| `incremental` | Large fact tables, CDC data | Appends/merges new records only |
| `ephemeral` | Intermediate calculations | Creates temp table, not directly queried |

### Incremental Model Config
```sql
{{ config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy='merge',  -- or 'delete+insert'
    partition_by={
      "field": "order_date",
      "data_type": "date",
      "granularity": "day"
    }
) }}
```

---

## Hooks Reference

### Pre-hook / Post-hook
```yaml
# In dbt_project.yml or model config
models:
  my_model:
    +pre-hook:
      - "CREATE TEMP TABLE temp_validation AS SELECT 1"
    +post-hook:
      - "GRANT SELECT ON {{ this }} TO analytics_role"
      - "COMMENT ON TABLE {{ this }} IS 'Created {{ run_started_at }}'"
```

### Hooks for Grants
```yaml
models:
  +post-hook:
    - "GRANT SELECT ON {{ this }} TO readonly_role"
    - "GRANT SELECT ON {{ this }} TO analytics_role"
```

---

## Orchestration Patterns

### Airflow DAG with dbt
```python
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

with DAG(
    'dbt_etl_pipeline',
    start_date=datetime(2024, 1, 1),
    schedule_interval='0 6 * * *',  # Daily at 6 AM
    catchup=False
) as dag:
    
    dbt_deps = BashOperator(
        task_id='dbt_deps',
        bash_command='cd /usr/app && dbt deps'
    )
    
    dbt_run_staging = BashOperator(
        task_id='dbt_run_staging',
        bash_command='cd /usr/app && dbt run --select staging --target prod'
    )
    
    dbt_run_marts = BashOperator(
        task_id='dbt_run_marts',
        bash_command='cd /usr/app && dbt run --select marts --target prod'
    )
    
    dbt_test = BashOperator(
        task_id='dbt_test',
        bash_command='cd /usr/app && dbt test --target prod'
    )
    
    dbt_source_freshness = BashOperator(
        task_id='dbt_source_freshness',
        bash_command='cd /usr/app && dbt source freshness --target prod'
    )
    
    dbt_deps >> dbt_run_staging >> dbt_run_marts >> dbt_test >> dbt_source_freshness
```

### GitHub Actions CI Pipeline
```yaml
# .github/workflows/dbt-ci.yml
name: dbt CI

on:
  pull_request:
    branches: [main]

jobs:
  dbt-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dbt
        run: pip install dbt-postgres
      - name: Run dbt
        env:
          DBT_PROD_PASSWORD: ${{ secrets.DBT_PROD_PASSWORD }}
        run: |
          dbt deps
          dbt run --target ci
          dbt test --target ci
```

---

## Exposures for BI Tools

Define in `models/example/schema.yml`:
```yaml
exposures:
  - name: orders_dashboard
    description: Executive overview of order metrics
    type: dashboard
    maturity: high
    owner:
      name: Analytics Team
      email: analytics@company.com
    depends_on:
      - ref('fct_orders')
      - ref('dim_customers')
    meta:
      tool: metabase
```

---

## dbt Artifacts

After running `dbt docs generate`, these files are created:

- `target/manifest.json` — Complete project manifest (all resources)
- `target/catalog.json` — Database catalog info (schemas, tables)
- `target/run_results.json` — Execution results
- `target/index.html` — Documentation website

---

## Common Issues & Solutions

### Issue: "Unknown model" error
**Solution:** Model not in `dbt_project.yml` under `models:` path. Check model path matches config.

### Issue: "Cannot find source" error
**Solution:** Source not defined in `schema.yml` under `sources:`. Run `dbt ls` to see recognized sources.

### Issue: `ref()` creates circular dependency
**Solution:** dbt doesn't allow cycles. Restructure to have a single direction (downstream).

### Issue: Incremental model has duplicates
**Solution:** Set `unique_key` correctly. Without it, dbt uses `merge` strategy incorrectly.

### Issue: Tests fail on not_null but column has nulls
**Solution:** Investigate data source. Fix upstream or use `COALESCE` in model.
