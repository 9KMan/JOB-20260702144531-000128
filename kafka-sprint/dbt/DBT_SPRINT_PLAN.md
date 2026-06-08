# dbt Developer Learning Sprint — 5-Day Plan

**Goal:** Go from zero to job-ready dbt developer in 5 days (2-3 hours/day)  
**Cost:** ~$0 using dbt Core + Docker + PostgreSQL (vs $50-100/month for dbt Cloud)  
**Prerequisites:** Basic SQL, Git, terminal comfort

---

## Day 1: dbt Core Foundations

### Morning Session (90 min) — Project Setup & First Models
**Objective:** Install dbt Core, connect to PostgreSQL, create your first models

**Tasks:**
- [ ] Install dbt Core with PostgreSQL adapter: `pip install dbt-postgres`
- [ ] Initialize project: `dbt init ecommerce_analytics`
- [ ] Configure `profiles.yml` for local PostgreSQL connection
- [ ] Explore auto-generated project structure:
  ```
  dbt_project.yml          # Project config
  models/example/          # Your SQL models
  macros/                  # Jinja macros
  tests/                   # Custom tests
  ```
- [ ] Create first staging model: `models/example/staging/stg_orders.sql`
- [ ] Run: `dbt run` and verify table created in PostgreSQL
- [ ] Generate docs: `dbt docs generate && dbt docs serve`

**Key Commands:**
```bash
dbt init ecommerce_analytics     # Create new project
dbt debug                         # Verify connection
dbt run                           # Run all models
dbt run --select stg_orders       # Run specific model
dbt ls                            # List all resources
```

### Afternoon Session (60 min) — Understanding ref() and source()
**Objective:** Master dependency management in dbt

**Tasks:**
- [ ] Define sources in `models/example/schema.yml` (orders, customers, products)
- [ ] Create staging model using `source()` function
- [ ] Create intermediate model using `ref()` to reference staging
- [ ] Create mart model using `ref()` to reference intermediate
- [ ] Visualize lineage: `dbt docs generate` and check lineage graph

**Core Concept:**
```sql
-- source() for raw tables (defined in schema.yml under sources)
SELECT * FROM {{ source('ecom', 'orders') }}

-- ref() for models (dbt manages dependencies automatically)
SELECT * FROM {{ ref('stg_orders') }}
```

**Success Criteria:** You can explain why `ref()` creates a DAG and `source()` does not

---

## Day 2: Jinja Templating & Macros

### Morning Session (90 min) — Jinja Fundamentals
**Objective:** Write SQL with Jinja for reusable, dynamic code

**Core Jinja Patterns:**
```sql
-- Variables
{% set table_name = 'orders' %}
SELECT * FROM {{ ref(table_name) }}

-- Conditionals
{% if is_incremental() %}
  WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}

-- Loops
{% for status in ['pending', 'processing', 'shipped'] %}
  '{{ status }}' as status_{{ loop.index }}
{% endfor %}

-- Macros
{{ datediff('order_date', 'ship_date', 'day') }}
```

**Tasks:**
- [ ] Create a macro `macros/optional_filter.sql` that conditionally adds WHERE clause
- [ ] Use `target` variable (dev/prod) in model logic
- [ ] Use `this` to reference current model
- [ ] Create macro for standard columns (created_at, updated_at)

### Afternoon Session (90 min) — Incremental Models & Testing
**Objective:** Build performant models with incremental strategy

**Tasks:**
- [ ] Convert a model to incremental: add `is_incremental()` check
- [ ] Configure `unique_key` and `incremental_strategy`
- [ ] Write generic tests in `schema.yml`:
  - not_null
  - unique
  - accepted_values
  - relationships
- [ ] Write a singular test (custom SQL validation)
- [ ] Run tests: `dbt test`

**Incremental Model Template:**
```sql
{{ config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy='delete+insert'
) }}

SELECT
    order_id,
    customer_id,
    order_date,
    total_amount
FROM {{ source('ecom', 'orders') }}

{% if is_incremental() %}
  WHERE order_date > (SELECT COALESCE(MAX(order_date), '1900-01-01') FROM {{ this }})
{% endif %}
```

**Success Criteria:** `dbt test` passes with zero failures

---

## Day 3: dbt Advanced — Snapshots, Seeds, Hooks, Packages

### Morning Session (90 min) — Snapshots & Seeds
**Objective:** Track historical changes and load static data

**Snapshots (Type 2 Slowly Changing Dimensions):**
```sql
-- models/snapshots/scd_customers.sql
{% snapshot scd_customers %}

{{
    config(
        target_schema='snapshots',
        strategy='timestamp',
        unique_key='customer_id',
        updated_at='updated_at',
        invalidate_hard_deletes=True
    )
}}

SELECT
    customer_id,
    customer_name,
    email,
    customer_tier,
    updated_at
FROM {{ source('ecom', 'customers') }}

{% endsnapshot %}
```

**Tasks:**
- [ ] Create snapshot for customer records (track tier changes)
- [ ] Create snapshot for product prices (track price changes)
- [ ] Use seeds for: tax rates, holiday calendars, country codes
- [ ] Run: `dbt seed` to load CSV data

### Afternoon Session (90 min) — Hooks & Packages
**Objective:** Automate repetitive tasks and extend dbt functionality

**Hooks:**
```yaml
# dbt_project.yml or model configs
on-run-start:
  - "{{ log('dbt run started at ' ~ run_started_at, info=True) }}"
  
models:
  example:
    +post-hook:
      - "GRANT SELECT ON {{ this }} TO analytics_role"
```

**Packages (dbt_utils + codegen):**
```yaml
# packages.yml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.1.1
  - package: dbt-labs/codegen
    version: 0.12.0
```

**Tasks:**
- [ ] Install packages: `dbt deps`
- [ ] Use `dbt_utils.star()` to select columns
- [ ] Use `dbt_utils.star()` with exclusions
- [ ] Use `codegen.generate_model_yaml` to scaffold schema.yml
- [ ] Create pre-hook to create temp table before model runs
- [ ] Create post-hook to add grants or indexes

---

## Day 4: dbt Cloud Features & Semantic Layer

### Morning Session (90 min) — dbt Cloud Overview (Self-Hosted Alternative)
**Objective:** Understand dbt Cloud features and implement equivalents

**dbt Cloud Features vs Self-Hosted:**
| Feature | Cloud | Self-Hosted Alternative |
|---------|-------|-------------------------|
| Job Scheduler | Built-in | Airflow, Cron |
| CI/CD | Native | GitHub Actions |
| Documentation | Hosted | `dbt docs serve` |
| Environment Management | Built-in | Git branches |
| Alerting | Built-in | Custom scripts |

**Tasks:**
- [ ] Set up GitHub Actions for `dbt run` on PR
- [ ] Create staging/prod environments via git branches
- [ ] Implement `dbt source freshness` check in CI
- [ ] Set up `dbt artifacts` upload to cloud storage

### Afternoon Session (90 min) — dbt Semantic Layer (Metrics)
**Objective:** Define metrics once, reuse across tools

**MetricFlow (dbt Semantic Layer):**
```yaml
# models/metrics/order_metrics.yml
metrics:
  - name: order_total_revenue
    label: Total Revenue
    model: ref('fct_orders')
    description: Sum of all order amounts
    
    calculation_method: sum
    expression: total_amount
    
    dimensions:
      - customer_tier
      - order_status
      - order_date
```

**Tasks:**
- [ ] Define 5 core business metrics (revenue, orders, customers)
- [ ] Create metrics for: MoM growth, average order value, customer lifetime value
- [ ] Understand how Metrics API replaces repeated metric calculations

**Success Criteria:** Can explain why metric definition should be centralized

---

## Day 5: Integration & Portfolio Project

### Morning Session (90 min) — dbt + Airflow + Snowflake/BigQuery

**Docker Compose Setup:**
```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ecommerce
      POSTGRES_USER: dbt_user
      POSTGRES_PASSWORD: dbt_password
    ports:
      - "5432:5432"
    
  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@dbt.local
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    
  dbt:
    image: dbt/dbt:1.7
    volumes:
      - ./:/usr/app
    working_dir: /usr/app
    command: sleep infinity
```

**Airflow DAG:**
```python
# dags/dbt_dag.py
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

with DAG('dbt_etl', start_date=datetime(2024, 1, 1), schedule_interval='@daily') as dag:
    dbt_run = BashOperator(
        task_id='dbt_run',
        bash_command='dbt run --target prod --profiles-dir /usr/app'
    )
    
    dbt_test = BashOperator(
        task_id='dbt_test',
        bash_command='dbt test --target prod --profiles-dir /usr/app'
    )
    
    dbt_docs = BashOperator(
        task_id='dbt_docs_generate',
        bash_command='dbt docs generate --target prod --profiles-dir /usr/app'
    )
    
    dbt_run >> dbt_test >> dbt_docs
```

**Tasks:**
- [ ] Set up Docker Compose with PostgreSQL + pgAdmin + dbt runner
- [ ] Connect dbt to Snowflake/BigQuery (if accounts available)
- [ ] Create Airflow DAG that runs `dbt run`, `dbt test`, `dbt source freshness`
- [ ] Implement CI/CD with GitHub Actions

### Afternoon Session (90 min) — Portfolio Project & Interview Prep

**Portfolio Project Ideas:**

1. **E-commerce Analytics Platform**
   - Sources: orders, customers, products, inventory
   - Marts: fct_orders, dim_customers, dim_products, int_order_items
   - Metrics: revenue, AOV, customer churn, inventory turnover
   - Expose to Metabase/Tableau via exposures

2. **Financial Data Warehouse**
   - Sources: transactions, accounts, fx_rates
   - Marts: fct_transactions, dim_accounts, fact_fx_conversions
   - Snapshots: account balances (SCD Type 2)
   - Metrics: P&L, balance sheet, cash flow

3. **Marketing Attribution Model**
   - Sources: sessions, clicks, conversions, campaigns
   - Marts: fct_sessions, int_channel_attribution
   - Metrics: ROAS, CPA, conversion rate by channel

**Success Criteria:**
- [ ] 3+ models in staging, 2+ in intermediate, 3+ in marts
- [ ] All models use `ref()` (no hardcoded table names)
- [ ] Generic tests on every primary key and foreign key
- [ ] At least 1 snapshot implemented
- [ ] `dbt docs generate` produces clean documentation
- [ ] GitHub Actions CI pipeline runs tests on PR

---

## Success Metrics

| Day | Deliverable | Validation |
|-----|-------------|------------|
| 1 | Project setup + first models | `dbt run` succeeds |
| 2 | Jinja macros + incremental | `dbt test` passes |
| 3 | Snapshots + seeds + hooks | Historical tracking works |
| 4 | Metrics + dbt Semantic Layer | Metrics defined |
| 5 | Full pipeline + portfolio | Ready for interviews |

---

## Key dbt Commands Cheat Sheet

```bash
# Setup & Config
dbt init <project_name>      # Create new project
dbt debug                    # Verify connections
dbt deps                     # Install packages

# Development
dbt run                      # Run all models
dbt run --select <model>     # Run specific model
dbt run --model +<model>     # Run model + upstream
dbt test                     # Run all tests
dbt test --select <model>    # Test specific model

# Documentation
dbt docs generate            # Generate docs
dbt docs serve               # Serve docs locally

# Advanced
dbt snapshot                 # Run snapshots
dbt seed                     # Load CSV seeds
dbt source freshness         # Check source data age
dbt build                    # Run + test + docs (full pipeline)

# Production
dbt run --target prod        # Run against prod
dbt run --exclude <selector> # Exclude models
```

---

## Next Steps After Sprint

1. **Get Certified:** dbt Analytics Engineering Certification (~$200)
2. **Contribute:** Submit PRs to dbt packages on GitHub
3. **Practice:** Solve dbt Core practice problems on Stack Overflow
4. **Deploy:** Set up dbt Cloud free trial for production experience
5. **Network:** Join dbt Community Slack (dbt Slack invite link)
