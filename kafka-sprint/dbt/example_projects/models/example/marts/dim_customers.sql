-- Dimension Model: dim_customers
-- Purpose: Dimension table for customers - one row per customer with enriched attributes
-- Materialization: table (customer count is typically low volume, table enables fast joins)
-- Type 1 SCD: We overwrite customer attributes when they change (latest values only)
-- For Type 2 SCD (tracking history), use snapshots instead

{{ config(
    materialized='table',
    schema='marts',
    tags=['marts', 'dimension', 'customers'],
    alias='dim_customers'
) }}

SELECT
    -- Primary key
    c.customer_id,
    
    -- Contact information
    c.email,
    c.first_name,
    c.last_name,
    c.full_name,
    
    -- Customer segmentation
    c.customer_tier,
    
    -- Customer value metrics (aggregated from orders)
    COALESCE(order_agg.first_order_date, c.created_at) AS first_order_date,
    COALESCE(order_agg.last_order_date, c.created_at) AS last_order_date,
    COALESCE(order_agg.total_orders, 0) AS total_orders,
    COALESCE(order_agg.total_spent, 0) AS total_spent,
    
    -- Average order value (AVG)
    CASE 
        WHEN COALESCE(order_agg.total_orders, 0) > 0 
        THEN ROUND(order_agg.total_spent / order_agg.total_orders, 2)
        ELSE 0 
    END AS average_order_value,
    
    -- Days since last order (recency)
    CURRENT_DATE - COALESCE(order_agg.last_order_date, c.created_at)::DATE AS days_since_last_order,
    
    -- Customer tenure (days since account creation)
    CURRENT_DATE - c.created_at::DATE AS customer_tenure_days,
    
    -- Customer lifecycle stage
    CASE 
        WHEN COALESCE(order_agg.total_orders, 0) = 0 THEN 'new'
        WHEN COALESCE(order_agg.total_orders, 0) <= 2 THEN 'active'
        WHEN COALESCE(order_agg.total_orders, 0) <= 5 THEN 'regular'
        ELSE 'VIP'
    END AS customer_lifecycle_stage,
    
    -- Tier eligibility check (based on lifetime spending)
    -- This helps identify customers who should be upgraded
    CASE
        WHEN c.customer_tier = 'bronze' AND COALESCE(order_agg.total_spent, 0) >= 500 THEN 'eligible_upgrade'
        WHEN c.customer_tier = 'silver' AND COALESCE(order_agg.total_spent, 0) >= 1000 THEN 'eligible_upgrade'
        WHEN c.customer_tier = 'gold' AND COALESCE(order_agg.total_spent, 0) >= 2500 THEN 'eligible_upgrade'
        WHEN c.customer_tier = 'platinum' THEN 'max_tier'
        ELSE 'not_eligible'
    END AS tier_upgrade_status,
    
    -- Metadata
    c.created_at,
    c.updated_at,
    CURRENT_TIMESTAMP AS dbt_updated_at
    
FROM {{ ref('stg_customers') }} c

-- Aggregate order metrics per customer
LEFT JOIN (
    SELECT 
        customer_id,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date,
        COUNT(*) AS total_orders,
        SUM(total_amount) AS total_spent
    FROM {{ ref('stg_orders') }}
    WHERE status NOT IN ('cancelled')
    GROUP BY customer_id
) order_agg ON c.customer_id = order_agg.customer_id
