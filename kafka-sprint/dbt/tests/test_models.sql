-- =============================================================================
-- Generic (Schema) Tests - Defined in schema.yml
-- These tests are automatically generated from the schema.yml definitions
-- Example of what dbt compiles these tests to:
-- =============================================================================

-- Test: dim_customers.customer_id UNIQUE
-- Compiled SQL that dbt runs:
/*
SELECT customer_id
FROM dim_customers
WHERE customer_id IS NULL
*/

-- Test: dim_customers.customer_id NOT NULL
-- Compiled SQL:
/*
SELECT customer_id
FROM dim_customers
WHERE customer_id IS NOT NULL
HAVING COUNT(*) = 0
*/

-- Test: fct_orders.status ACCEPTED VALUES
-- Compiled SQL:
/*
SELECT DISTINCT status
FROM fct_orders
WHERE status NOT IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')
*/

-- =============================================================================
-- Singular (Custom) Tests - Stored as SQL files in tests/
-- These return 0 rows if test passes, >0 rows if test fails
-- =============================================================================

-- Test: check_order_revenue_integrity.sql
-- Validates that fct_orders.total_amount matches the sum of int_order_items.line_total
-- This catches data quality issues where order totals don't match line items

SELECT
    o.order_id,
    o.total_amount AS order_total,
    SUM(oi.line_total) AS line_item_sum,
    o.total_amount - SUM(oi.line_total) AS discrepancy,
    CURRENT_TIMESTAMP AS tested_at
FROM {{ ref('fct_orders') }} o
LEFT JOIN {{ ref('int_order_items') }} oi ON o.order_id = oi.order_id
GROUP BY o.order_id, o.total_amount
HAVING ABS(o.total_amount - COALESCE(SUM(oi.line_total), 0)) > 0.01
-- Test passes if this query returns 0 rows
-- Any row returned indicates an order where total doesn't match line items


-- =============================================================================

-- Test: check_duplicate_order_items.sql
-- Ensures no duplicate order_item_id exists (idempotency check)

SELECT
    order_item_id,
    COUNT(*) AS occurrence_count,
    CURRENT_TIMESTAMP AS tested_at
FROM {{ ref('int_order_items') }}
GROUP BY order_item_id
HAVING COUNT(*) > 1
-- Test passes if this query returns 0 rows


-- =============================================================================

-- Test: check_customer_order_sequence.sql  
-- Validates that customer first_order_date in dim_customers matches MIN(order_date) in fct_orders
-- Catches cases where customer dimension gets out of sync with order facts

SELECT
    c.customer_id,
    c.first_order_date AS dim_first_order,
    MIN(o.order_date) AS fact_first_order,
    CURRENT_TIMESTAMP AS tested_at
FROM {{ ref('dim_customers') }} c
JOIN {{ ref('fct_orders') }} o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.first_order_date
HAVING c.first_order_date != MIN(o.order_date)::DATE
-- Test passes if this query returns 0 rows


-- =============================================================================

-- Test: check_order_date_shipped_sequence.sql
-- Validates business rule: ship_date must be >= order_date

SELECT
    o.order_id,
    o.order_date,
    oi.ship_date,
    oi.ship_date - o.order_date AS days_to_ship,
    CURRENT_TIMESTAMP AS tested_at
FROM {{ ref('fct_orders') }} o
JOIN {{ ref('int_shipments') }} oi ON o.order_id = oi.order_id
WHERE oi.ship_date < o.order_date
-- Test passes if this query returns 0 rows


-- =============================================================================

-- Test: check_negative_order_amounts.sql
-- Flags any orders with negative amounts that might indicate refunds or data issues

SELECT
    order_id,
    total_amount,
    status,
    CURRENT_TIMESTAMP AS tested_at
FROM {{ ref('fct_orders') }}
WHERE total_amount < 0
AND status != 'refunded'
-- Test passes if this query returns 0 rows


-- =============================================================================

-- Test: check_stale_customers.sql
-- Identifies customers who haven't placed an order in >180 days (churn risk)

SELECT
    customer_id,
    last_order_date,
    CURRENT_DATE - last_order_date::DATE AS days_since_order,
    total_orders,
    total_spent,
    CURRENT_TIMESTAMP AS tested_at
FROM {{ ref('dim_customers') }}
WHERE last_order_date < CURRENT_DATE - INTERVAL '180 days'
AND total_orders > 0  -- Exclude customers who never ordered
-- Test passes if this query returns 0 rows (no stale customers flagged)


-- =============================================================================

-- Test: check_null_foreign_keys.sql
-- Ensures all foreign keys can be resolved (data integrity)

SELECT
    order_id,
    customer_id,
    CURRENT_TIMESTAMP AS tested_at
FROM {{ ref('fct_orders') }}
WHERE customer_id IS NULL
-- Test passes if this query returns 0 rows


-- =============================================================================

-- Test: check_revenue_by_day_variance.sql
-- Flags days where revenue deviates more than 3 standard deviations (anomaly detection)

WITH daily_revenue AS (
    SELECT 
        order_date_day,
        SUM(total_amount) AS daily_revenue
    FROM {{ ref('fct_orders') }}
    GROUP BY order_date_day
),
stats AS (
    SELECT 
        AVG(daily_revenue) AS avg_revenue,
        STDDEV(daily_revenue) AS stddev_revenue
    FROM daily_revenue
)
SELECT
    dr.order_date_day,
    dr.daily_revenue,
    s.avg_revenue,
    s.stddev_revenue,
    (dr.daily_revenue - s.avg_revenue) / NULLIF(s.stddev_revenue, 0) AS z_score,
    CURRENT_TIMESTAMP AS tested_at
FROM daily_revenue dr
CROSS JOIN stats s
WHERE ABS((dr.daily_revenue - s.avg_revenue) / NULLIF(s.stddev_revenue, 0)) > 3
-- Test passes if this query returns 0 rows (no anomalous days)
