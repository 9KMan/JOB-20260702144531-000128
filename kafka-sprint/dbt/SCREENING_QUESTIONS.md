# dbt Developer Screening Questions

## 15 Interview Questions with Detailed Answers

---

## Q1: Explain dbt's model layers (staging, intermediate, marts). Why is this structure important?

**Answer:**

In dbt projects, I organize models into three distinct layers that reflect the transformation maturity:

**Staging Layer (models/example/staging/):** This is the first transformation layer where I bring raw source data into dbt. Each staging model typically corresponds to a single source table, giving it a clean, documented interface. I rename columns to snake_case, add prefixes (like `stg_`), cast data types explicitly, and select only the columns needed downstream. For example, `stg_orders.sql` wraps `source('ecom', 'orders')` and provides a clean contract for all downstream models.

**Intermediate Layer (models/example/intermediate/):** These are multi-source transformations that don't yet represent business entities. I use intermediate models to handle cross-cutting concerns like joining orders with customer data, unions across multiple sources, or complex business logic that will be reused by multiple mart models. Intermediate models are building blocks.

**Marts Layer (models/example/marts/):** These are the final analytical models designed for consumption by BI tools, dashboards, and analysts. I separate them into:
- **Fact tables (fct_)** — Transaction-level records with foreign keys to dimensions, additive numeric measures (amounts, quantities), and one row per business event (e.g., one row per order)
- **Dimension tables (dim_)** — Descriptive attributes about people, places, things (e.g., dim_customers with customer_name, email, customer_tier)

**Why this structure matters:** It creates a clear data lineage DAG, enables selective model runs (run only staging before marts), separates concerns between raw ingestion and business logic, and makes the project self-documenting. Anyone can open the project and immediately understand the data flow from raw source to business insight.

---

## Q2: What is the difference between snapshots and incremental models? When would you use each?

**Answer:**

Snapshots and incremental models solve different problems in dbt, and understanding when to use each is fundamental to building reliable data pipelines.

**Snapshots** implement Slowly Changing Dimension (SCD) Type 2 tracking. I use snapshots when I need to track the historical state of a record at specific points in time. When a record changes in the source system, the snapshot preserves the old record (with dbt_valid_from/dbt_valid_to columns) and inserts a new record with the new values. For example, if a customer's tier changes from 'silver' to 'gold', a snapshot will have two records: one showing 'silver' with its valid date range, and a new record showing 'gold'. This enables point-in-time analysis — I can ask "what was this customer's tier on January 1st?"

**Incremental models** are for high-volume fact tables where I want to process only new or changed records since the last run. Instead of reprocessing the entire table, I use a condition (usually based on updated_at or a watermark) to select only new records and insert them into the existing table. This is critical for large fact tables like order events or web analytics where full recomputation would be prohibitively expensive.

**When to use snapshots:**
- Tracking changes to dimension attributes (customer address, product price, employee department)
- Any scenario requiring point-in-time analysis
- Compliance or audit requirements needing historical record states

**When to use incremental models:**
- Large fact tables with high volume (orders, transactions, log events)
- CDC (change data capture) scenarios where only changes arrive
- When near-real-time data freshness is required

The key distinction: snapshots preserve historical versions of records with their validity periods; incremental models just append new records and don't typically update historical records.

---

## Q3: What is the difference between singular and generic tests in dbt? Give examples of when to use each.

**Answer:**

dbt provides two complementary testing approaches that I use together for comprehensive data validation.

**Generic tests (also called schema tests)** are defined declaratively in `schema.yml` and are reusable — one definition can apply to multiple columns across models. They're written as parameterized SQL queries that pass if they return zero rows and fail if any rows are returned. dbt ships with four built-in generic tests: `unique`, `not_null`, `accepted_values`, and `relationships`. When I write `not_null` on `customer_id`, dbt compiles it to: `SELECT customer_id FROM dim_customers WHERE customer_id IS NULL` and fails if any results exist.

**Singular tests (also called custom tests)** are one-off SQL queries stored in `.sql` files under the `tests/` directory. They're written as explicit SQL that should return zero rows for the test to pass. I use singular tests for business logic validation that can't be expressed with generic test parameters.

**When to use generic tests:**
- Primary key uniqueness and non-nullness across all tables (automate this)
- Foreign key referential integrity (relationships test)
- Enum/enumerated field validation (accepted_values)
- Any test that follows a standard pattern across multiple columns

**When to use singular tests:**
- Complex cross-table business rules (e.g., order.total_amount equals sum of line items)
- Date range validations (e.g., ship_date must be >= order_date)
- Statistical anomaly detection (e.g., flag orders 10x above average)
- Custom error messages specific to your business

**Best practice:** I typically start with generic tests for schema validation as code, then add singular tests for business logic validation. The combination gives me confidence that both the structure (no null PKs, valid foreign keys) and the semantics (revenue equals sum of line items) are correct.

---

## Q4: Explain how macros and Jinja loops work in dbt. Provide a practical example of a macro you would create.

**Answer:**

Jinja is the templating engine that makes dbt powerful. It allows me to write SQL that is dynamic, reusable, and parameterized. At its core, Jinja lets me embed logic (conditionals, loops, variables) into SQL that gets evaluated before the SQL is sent to the database.

**Variables and Sets:**
```sql
{% set table_name = 'orders' %}
{% set excluded_columns = ['password', 'token', 'secret'] %}

SELECT {{ dbt_utils.star(ref('orders'), except=excluded_columns) }}
FROM {{ ref(table_name) }}
```

**Conditionals:**
```sql
{% if target.name == 'prod' %}
    WHERE processed = true
{% else %}
    WHERE 1=1
{% endif %}
```

**Loops:**
```sql
{% for status in ['pending', 'processing', 'shipped', 'delivered'] %}
    SUM(CASE WHEN order_status = '{{ status }}' THEN 1 ELSE 0 END) AS {{ status }}_count
    {% if not loop.last %},{% endif %}
{% endfor %}
```

**Practical macro example — optional filter:**
```sql
-- macros/optional_filter.sql
{% macro optional_filter(table_alias, column_name, operator, value, condition) %}
    {% if condition %}
        AND {{ table_alias }}.{{ column_name }} {{ operator }} {{ value }}
    {% endif %}
{% endmacro %}
```

I would use this macro like:
```sql
SELECT *
FROM {{ ref('orders') }} o
WHERE 1=1
{{ optional_filter('o', 'status', '=', "'shipped'", var('include_shipped', false)) }}
```

**Another common pattern — surrogate key:**
```sql
{% macro surrogate_key(columns) %}
    {%- for col in columns -%}
        COALESCE(CAST({{ col }} AS VARCHAR), '~'){%- if not loop.last %} || '|' || {% endif -%}
    {%- endfor -%}
{% endmacro %}
```

The key insight is that macros let me DRY (don't repeat yourself) out repetitive SQL patterns. Instead of writing the same CASE statement structure 10 times, I write a macro once and call it with different parameters.

---

## Q5: Compare dbt_utils and codegen packages. When would you use each?

**Answer:**

Both dbt-labs/dbt_utils and dbt-labs/codegen are essential packages that serve different purposes: dbt_utils provides utility functions and patterns for transformation logic, while codegen provides scaffolding and code generation to speed up development.

**dbt_utils — Transformation Utilities:**
dbt_utils is my workhorse for writing transformation SQL. Key functions I use frequently:

- `star()` — Select all columns from a table, optionally excluding certain ones. Eliminates hardcoding of column lists when source tables change.
```sql
SELECT {{ dbt_utils.star(from=ref('orders'), except=['password']) }}
```

- `surrogate_key()` — Create a deterministic hash key from multiple columns. Critical for creating composite primary keys in dimensions.
```sql
{{ dbt_utils.surrogate_key(['customer_id', 'order_date']) }}
```

- `date_diff()` — Calculate difference between two dates in specified units
```sql
{{ dbt_utils.date_diff('order_date', 'ship_date', 'day') }}
```

- `pivot()` — Generate pivot queries dynamically
```sql
{{ dbt_utils.pivot(column='status', values=['pending','shipped']) }}
```

- `get_column_values()` — Dynamically get distinct values from a column for use in Jinja loops

**codegen — Code Scaffolding:**
codegen generates YAML and SQL skeleton files, saving manual work:

- `generate_model_yaml()` — Creates schema.yml skeleton with columns from an existing model
- `generate_source_yaml()` — Creates source definitions from raw database tables
- `generate_base_model()` — Creates staging model skeleton with column definitions

**When to use dbt_utils:** Whenever I need to write transformation logic. The surrogate_key alone is worth the dependency — it handles null coalescing properly and produces consistent hashes.

**When to use codegen:** When starting a new project or adding models to an existing one. I'll use `codegen.generate_model_yaml()` to scaffold the schema.yml, then fill in tests and descriptions. It's faster than typing column lists manually.

**My practice:** I include both packages in every project. dbt_utils is used constantly in models; codegen is used periodically when adding new sources or models.

---

## Q6: What is dbt source freshness and how do you configure it?

**Answer:**

dbt source freshness is a feature that monitors whether your raw source data is being loaded on schedule. It answers the question: "How old is the data in my staging tables?" This is critical for data teams because downstream reports are only as timely as their upstream sources.

**How it works:**

I define a `source` in `schema.yml` with a `freshness` block:
```yaml
sources:
  - name: ecom
    tables:
      - name: orders
        freshness:
          warn_after: {count: 12, period: hour}
          error_after: {count: 24, period: hour}
        loaded_at_field: updated_at
      - name: customers
        freshness:
          warn_after: {count: 1, period: day}
          error_after: {count: 7, days}
        loaded_at_field: last_loaded_at
```

The `loaded_at_field` is a timestamp column in the source that indicates when the record was last loaded. dbt compares the max value of this column against the current time to determine freshness.

**Running freshness checks:**
```bash
dbt source freshness                    # Check all sources
dbt source freshness --select source:ecom  # Check specific source
```

**In CI/CD pipelines:**
```bash
dbt source freshness --project-cache freshness && \
  echo "All sources fresh" || echo "Sources stale - investigate!"
```

**Output interpretation:**
- If the max `loaded_at_field` is within `warn_after`: Source is fresh
- If it exceeds `warn_after` but not `error_after`: Warning (but pipeline continues)
- If it exceeds `error_after`: Error (pipeline should halt, alert sent)

**Why it matters:** Without freshness monitoring, an analyst might report on stale data without knowing the upstream pipeline failed. Source freshness makes data age visible and actionable.

---

## Q7: What is the difference between hooks, pre-hook, and post-hook in dbt?

**Answer:**

Hooks in dbt are SQL statements or commands that execute at specific points in the model lifecycle. They're the automation layer for repetitive database operations that would otherwise clutter model SQL.

**Pre-hook:** Executes BEFORE the model SQL runs. I use this for setup operations like creating temporary objects or validating preconditions.

**Post-hook:** Executes AFTER the model SQL completes successfully. I use this for cleanup, security, or metadata operations.

**Hooks vs Model Config:**
- **Hooks in `dbt_project.yml`:** Apply to ALL models (global)
- **Hooks in model `config()`:** Apply to specific model

**Common use cases for pre-hook:**
```sql
-- Create temp table for validation
{{ config(pre_hook="CREATE TEMP TABLE validation_check AS SELECT 1") }}
```

**Common use cases for post-hook:**
```sql
-- Grant permissions to analytics role
{{ config(post_hook="GRANT SELECT ON {{ this }} TO analytics_role") }}

-- Add comment to table for documentation
{{ config(post_hook="COMMENT ON TABLE {{ this }} IS 'Last refreshed: {{ run_started_at }}'") }}

-- Rebuild indexes (for certain databases)
{{ config(post_hook="REINDEX TABLE {{ this }}") }}
```

**Practical example — audit trail:**
```sql
{{ config(
    post_hook=[
        "INSERT INTO audit.log_table_history (table_name, run_at, rows_affected) VALUES ('{{ this }}', '{{ run_started_at }}', {{ dbt_utils.star(ref('fct_orders')) }})"
    ]
) }}
```

**In practice, the most valuable hooks I use are:**
1. **Security grants** — Automating `GRANT SELECT` to roles (critical for production)
2. **Table comments** — Documenting tables in the database catalog automatically
3. **Statistics collection** — Telling the database to update statistics after load

The key difference from `on-run-start`/`on-run-end` (which run once per dbt invocation): hooks run after each individual model.

---

## Q8: How do exposures work in dbt and why are they important for BI tool integration?

**Answer:**

Exposures in dbt are metadata declarations that describe how dbt models are consumed by downstream tools — BI dashboards, reverse ETL tools, machine learning pipelines, or any external system that reads from your data warehouse. They create a bidirectional lineage map: dbt knows what models feed into which dashboards, and the BI tool can see back to the source tables.

**Defining an exposure:**
```yaml
# In models/example/schema.yml
exposures:
  - name: weekly_revenue_dashboard
    description: Executive summary showing weekly revenue trends and order volumes
    type: dashboard
    maturity: high
    owner:
      name: Finance Team
      email: finance@company.com
    depends_on:
      - ref('fct_orders')
      - ref('dim_customers')
    meta:
      tool: tableau
      dashboard_url: https://tableau.company.com/views/Revenue_001

  - name: customer360_model
    description: Customer360 feature store for ML recommendations
    type: application
    maturity: medium
    owner:
      name: ML Platform Team
      email: ml@company.com
    depends_on:
      - ref('dim_customers')
      - ref('fct_orders')
      - ref('int_customer_features')
```

**Why exposures matter:**

1. **Impact analysis:** Before changing a model, I can query what dashboards depend on it. If I'm modifying `dim_customers`, I immediately know 3 dashboards will be affected.

2. **Documentation:** The exposure is the contract between the data engineering team and BI analysts. It documents what's available and how it's meant to be used.

3. **Freshness tracking:** dbt can surface dashboard staleness in the documentation site. If `fct_orders` hasn't refreshed in 48 hours, the weekly_revenue_dashboard shows as stale.

4. **CI/CD guardrails:** In a mature pipeline, I can configure CI to block deployments if a model with downstream exposures is changed in breaking ways.

**Supported exposure types:** dashboard, notebook, analysis, application, ml_model, seed

**The meta field:** The `meta` field is flexible — I use it to store tool-specific information like Tableau dashboard URL, Looker look IDs, or any custom metadata your organization needs.

---

## Q9: Compare dbt Cloud scheduler vs Airflow orchestration. When would you choose one over the other?

**Answer:**

This is a critical architectural decision for any data platform. Both schedule and orchestrate dbt runs, but they serve different purposes and have different trade-offs.

**dbt Cloud Scheduler:**
- Native dbt experience with zero infrastructure to manage
- Environment management (dev/staging/prod) built in
- Job scheduling with cron-like syntax
- Built-in CI/CD via dbt Cloud's PR integration
- Native alerting and notification system
- Costs $50-100/month depending on features

**Airflow Orchestration:**
- General-purpose workflow orchestrator (dbt is just one task type)
- Full control over infrastructure
- Complex dependency graphs with branching logic
- Can orchestrate dbt alongside Python ETL, API calls, Spark jobs, etc.
- Strong community and enterprise support (Astronomer, MWAA)
- Requires more operational overhead

**When to choose dbt Cloud:**
- Small to medium teams without dedicated platform engineers
- Pure dbt workloads (no complex multi-tool pipelines)
- Fast onboarding priority — get running in hours, not days
- Willing to pay subscription for managed service
- Teams already using dbt Cloud for discovery and development

**When to choose Airflow:**
- Complex hybrid pipelines (dbt + Spark + Python + API integrations)
- Existing Airflow investment with strong operational expertise
- Need fine-grained control over retry logic, SLAs, and alerting
- Multi-team environment where dbt is just one component
- Compliance requirements mandate specific infrastructure

**Hybrid approach (what I often implement):**
Use dbt Cloud for development and exploration (its IDE and scheduling UI are excellent), but orchestrate production pipelines in Airflow for operational control. dbt Cloud triggers via API:
```bash
# From Airflow, trigger dbt Cloud job
curl -X POST https://cloud.getdbt.com/api/v2/jobs/{job_id}/run/ \
  -H "Authorization: Token {api_token}"
```

The key insight: dbt Cloud is a dbt-first platform; Airflow is a workflow-first platform. If dbt is your primary tool and team is small, Cloud wins. If you're building a complex data platform with multiple tools, Airflow provides the flexibility you need.

---

## Q10: When would you use ref() vs source() in dbt? What's the practical difference?

**Answer:**

The `ref()` and `source()` functions are the two ways models in dbt reference other tables, but they serve fundamentally different purposes in the data architecture.

**source() — For raw, external data:**
```sql
-- References tables that exist in the warehouse but are NOT dbt models
-- Defined in schema.yml under the 'sources:' key
SELECT * FROM {{ source('ecom', 'orders') }}
```

Sources represent data ingested from external systems — your CRM, payment processor, Shopify store, Salesforce, etc. They are the entry points into dbt's world. When I write `source('ecom', 'orders')`, I'm telling dbt: "This table was not created by dbt; it was loaded by an external process (Fivetran, Airbyte, custom ETL)."

**ref() — For dbt-managed models:**
```sql
-- References other dbt models (which dbt compiles to actual tables/views)
SELECT * FROM {{ ref('stg_orders') }}
```

When I write `ref('stg_orders')`, dbt looks up that model in the project, determines its schema and table name based on current target, and compiles it. Importantly, `ref()` creates a dependency in dbt's DAG — dbt knows `fct_orders` depends on `stg_orders` and will run them in the correct order.

**The practical rule I follow:**
- **First transformation from raw data** → Use `source()` in the staging model
- **All subsequent transformations** → Use `ref()` to reference other dbt models

**Example full lineage:**
```sql
-- STAGING: First touch of raw data
SELECT order_id, customer_id, order_date, status
FROM {{ source('ecom', 'orders') }}

-- INTERMEDIATE: Combines staging models
SELECT o.order_id, o.customer_id, c.customer_name
FROM {{ ref('stg_orders') }} o
JOIN {{ ref('stg_customers') }} c ON o.customer_id = c.customer_id

-- MART: Final business table
SELECT order_id, customer_id, customer_name, order_date
FROM {{ ref('int_order_customers') }}
```

**Why this matters:**
1. dbt's DAG is built entirely on `ref()` dependencies (sources are roots)
2. `dbt run` respects dependency order automatically
3. `dbt ls --妹妹+` can traverse the graph upstream or downstream
4. Lineage in documentation shows the full data flow

Never use `source()` to reference a dbt model, and never hardcode schema names — always use `ref()` so dbt manages the dependency graph.

---

## Q11: How do you handle late-arriving facts in incremental models?

**Answer:**

Late-arriving facts is a common data warehouse challenge where a business event (like an order) arrives into the source system hours or days after it occurred. In incremental models, this creates a tricky problem: if I use `order_date` as my watermark, late-arriving orders might never be picked up if their `order_date` is older than my last processed record.

**The naive incremental approach (problematic):**
```sql
{{ config(materialized='incremental') }}

SELECT order_id, customer_id, order_date, amount
FROM {{ source('ecom', 'orders') }}

{% if is_incremental() %}
  WHERE order_date > (SELECT MAX(order_date) FROM {{ this }})
{% endif %}
```

This fails because a late-arriving order from 3 days ago won't be picked up when the daily job runs tomorrow.

**Solution 1: Use updated_at instead of event date:**
```sql
{% if is_incremental() %}
  WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```

This picks up any record where the source row changed, regardless of when the order actually occurred. However, this can cause duplicate processing if a record truly has no updates.

**Solution 2: Composite watermark (recommended for strict requirements):**
```sql
{{ config(materialized='incremental', unique_key='order_id') }}

SELECT order_id, customer_id, order_date, updated_at, amount
FROM {{ source('ecom', 'orders') }}

{% if is_incremental() %}
  WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
     OR order_id NOT IN (SELECT order_id FROM {{ this }})
{% endif %}
```

This dual condition: (1) picks up genuinely new records, AND (2) picks up late-arriving facts where the order_id wasn't in our table yet.

**Solution 3: Use a different extraction pattern:**
For truly late-arriving facts, consider whether incremental is the right strategy. Some teams use:
- Full reload of the fact table weekly
- A "catch-up" job that looks back 7 days every hour
- CDC-based extraction with offset tracking

**My practice:** I document the late-arriving fact policy with stakeholders. For most e-commerce order data, a 24-48 hour lag is acceptable. If business requirements demand strict completeness, I implement Solution 2 with a 7-day lookback on the `OR` clause.

---

## Q12: Explain the difference between the World of Effects (dbt External Metrics) and dbt Semantic Layer.

**Answer:**

This question is slightly ahead of the current dbt Semantic Layer rollout, but the concepts are important to understand for modern data architecture.

**dbt Semantic Layer (MetricFlow) — Current offering:**

dbt Semantic Layer is dbt Labs' native approach to metric standardization, launched around dbt 1.6/1.7. It allows you to define metrics as code in YAML:

```yaml
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
      - order_date: day
```

The key innovation is that metrics are defined once, in one place, and can be queried via the Metrics API or in downstream tools (Tableau, Looker, Hex) that connect via the dbt Semantic Layer API. When the underlying model changes, metrics update automatically — no need to update calculations across multiple BI tools.

**World of Effects (WOE) — Future direction / theoretical concept:**

World of Effects is a theoretical framework (sometimes discussed in dbt community contexts) around cause-and-effect relationships in data transformations. It emphasizes understanding how changes in upstream data propagate through transformations to affect downstream outputs.

In practical terms, World of Effects thinking influences:
- Better DAG design to minimize hidden dependencies
- Impact analysis before model changes
- Lineage-based alerting (notify on downstream effects, not just upstream breaks)

**The key difference:**

dbt Semantic Layer is a concrete product for centralizing metric definitions. World of Effects is a conceptual framework for thinking about data transformation dependencies. They complement each other: the Semantic Layer makes metrics explicit and reusable, while WOE thinking helps you design models that are more maintainable and understandable.

**For job readiness:** Know that dbt Semantic Layer is production and valuable for reducing metric inconsistency across BI tools. Define metrics in dbt YAML, query via API, and eliminate the "why is this number different in Tableau vs Looker?" problem.

---

## Q13: How do you performance-tune dbt models? Discuss unique_key, partitions, and other strategies.

**Answer:**

Performance tuning in dbt happens at multiple levels: the SQL level, the model materialization level, and the warehouse configuration level.

**unique_key — Critical for incremental models:**

Without `unique_key`, dbt's merge strategy can't identify which rows to update. It will either duplicate data or fail. For my order fact table:
```sql
{{ config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy='merge'
) }}
```

For composite keys, use dbt_utils.surrogate_key:
```sql
{{ config(
    unique_key=dbt_utils.surrogate_key(['customer_id', 'order_date', 'order_line'])
) }}
```

**Partitioning — For large tables:**

Snowflake and BigQuery support table partitioning which dramatically improves query performance:

```sql
{{ config(
    materialized='incremental',
    partition_by={
      "field": "order_date",
      "data_type": "date",
      "granularity": "day"
    },
    cluster_by=['customer_id', 'status']
) }}
```

For Snowflake, also specify clustering keys at table creation.

**SQL-level optimizations:**

1. **Filter early** — Push WHERE clauses to the most upstream model
2. **Select only needed columns** — Don't `SELECT *` in production models
3. **Avoid cartesian joins** — Always include join conditions
4. **Use appropriate data types** — Don't store strings when dates/numbers work

**Materialization strategies:**

| Strategy | When to use |
|----------|-------------|
| `view` | Large tables queried frequently but written rarely |
| `table` | Small tables, snapshots, heavily filtered subsets |
| `incremental` | Large fact tables, CDC data |
| `ephemeral` | Intermediate CTEs reused across models |

**Warehouse-level tuning:**
- Snowflake: Right-size warehouse for workload (scale up for batch, down for light queries)
- BigQuery: Use slot reservations for consistent performance
- PostgreSQL: Configure `effective_cache_size` and `shared_buffers`

**My diagnostic approach:** Run `EXPLAIN` on slow queries, check warehouse utilization during runs, monitor dbt's `invocation_id` timing in `run_results.json`, and profile long-running models with query execution logs.

---

## Q14: What are dbt artifacts and how do you use them for data governance?

**Answer:**

dbt artifacts are JSON files generated by dbt commands that contain complete metadata about your project. They are the foundation for governance, documentation, and lineage tracking.

**Primary artifacts:**

**manifest.json** — The complete project graph:
- All models, seeds, snapshots, tests, macros
- Dependency DAG structure
- File paths and resource metadata
```json
{
  "nodes": {
    "model.dbt.fct_orders": {
      "resource_type": "model",
      "unique_id": "model.dbt.fct_orders",
      "depends_on": {"nodes": ["model.dbt.stg_orders"]},
      "refs": [{"name": "stg_orders"}]
    }
  }
}
```

**catalog.json** — Database catalog information:
- Column names, types, sizes
- Table and column descriptions
- Statistics (row counts, disk usage)

**run_results.json** — Execution results:
- Timing for each model (total, execution, planning)
- Test pass/fail counts
- Errors encountered

**sources.json** — Source freshness results:
- Freshness status per source
- Last loaded timestamps

**How I use artifacts for governance:**

**1. Automatic documentation:** `dbt docs generate` reads manifest.json and catalog.json to build the documentation site. Column descriptions defined in schema.yml appear automatically.

**2. Lineage tracking:** The `depends_on` structure in manifest.json enables dbt to show the full upstream/downstream lineage for any model. This is critical for impact analysis.

**3. Data contract enforcement:**
```sql
-- In CI/CD, compare artifacts to detect breaking changes
dbt ls --output json > current_models.json
git diff main -- artifacts.json | grep '"resource_type": "model"'
```

**4. Stakeholder communication:**
```python
# Python script to extract model documentation for a stakeholder
import json
with open('target/manifest.json') as f:
    manifest = json.load(f)

for node in manifest['nodes'].values():
    if node['resource_type'] == 'model':
        print(f"{node['name']}: {node['description']}")
```

**5. dbt Cloud governance features (if using Cloud):**
- Column-level lineage
- Business glossary integration
- Ownership assignment and approval workflows

**Best practice:** Commit artifacts to git (or store in cloud storage) for historical tracking. Compare artifacts between runs to detect unexpected model changes.

---

## Q15: How do you enforce data contracts in dbt? Discuss dbt + data contract integration.

**Answer:**

Data contracts are agreements between data producers (engineering) and data consumers (analysts, BI tools) about data quality, freshness, and schema. dbt is the ideal layer for enforcement because it sits between raw data and consumption.

**Contract enforcement points in dbt:**

**1. Source contracts (schema enforcement):**
```yaml
sources:
  - name: ecommerce
    freshness:
      warn_after: {count: 12, period: hour}
      error_after: {count: 24, period: hour}
    tables:
      - name: orders
        columns:
          - name: order_id
            data_type: string
            contract:
              enforced: true
          - name: amount
            data_type: numeric
            contract:
              enforced: true
        constraints:
          - name: orders_pk
            type: primary_key
            columns: [order_id]
```

**2. Model contracts:**
```yaml
models:
  - name: fct_orders
    contract:
      enforced: true
    columns:
      - name: order_id
        data_type: string
        description: Primary key
      - name: customer_id
        data_type: string
      - name: order_date
        data_type: timestamp
```

When `contract.enforced: true`, dbt validates that the model output matches the contract schema. If a model produces a column not in the contract (or wrong data type), dbt fails the run.

**3. Tests as contract validation:**
```yaml
- name: order_id
  tests:
    - not_null
    - unique
    - relationships:
        to: ref('dim_customers')
        field: customer_id
```

**4. dbt Semantic Layer for metric contracts:**
```yaml
metrics:
  - name: order_total_revenue
    label: Total Revenue
    description: Sum of order amounts in USD
    calculation_method: sum
    expression: total_amount
    dimensions:
      - customer_tier
```

This creates a metric contract — any BI tool querying via the Metrics API gets the same number.

**CI/CD integration for contracts:**

```yaml
# .github/workflows/dbt-contracts.yml
name: dbt Contract Enforcement

on:
  pull_request:

jobs:
  enforce-contracts:
    runs-on: ubuntu-latest
    steps:
      - name: Run dbt with contract enforcement
        run: |
          dbt run --model +marts --defer --state ./target
          dbt test --model +marts
      - name: Check source freshness
        run: dbt source freshness
```

**My practice for data contract implementation:**

1. **Define contracts at the source level** — What do we expect from external data?
2. **Define contracts at the mart level** — What do consumers expect from us?
3. **Enforce in CI** — Block PRs that break contracts
4. **Document exceptions** — Sometimes contracts need waivers (temporary nulls, legacy schema)

dbt's contract enforcement turns implicit expectations into explicit, automated validation — eliminating the "I thought this column would always be populated" surprises.
