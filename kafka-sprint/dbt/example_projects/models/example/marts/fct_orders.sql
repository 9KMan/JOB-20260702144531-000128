-- Mart Model: fct_orders
-- Purpose: Fact table for orders - one row per order with denormalized customer details
-- Materialization: incremental (high volume, append-only fact table)
-- This is the core business table for revenue and order analytics

{{ config(
    materialized='incremental',
    schema='marts',
    tags=['marts', 'fact', 'orders'],
    alias='fct_orders',
    unique_key='order_id',
    incremental_strategy='merge',
    partition_by={
        'field': 'order_date',
        'data_type': 'date',
        'granularity': 'day'
    }
) }}

-- Use is_incremental() to only process new/changed orders
-- This dramatically improves performance for large order histories

SELECT
    -- Primary key
    o.order_id,
    
    -- Foreign keys
    o.customer_id,
    
    -- Denormalized customer attributes (snapshot at time of order)
    c.full_name AS customer_name,
    c.customer_tier,
    c.email AS customer_email,
    
    -- Date/Time dimensions
    o.order_date,
    DATE_TRUNC('day', o.order_date) AS order_date_day,
    DATE_TRUNC('week', o.order_date) AS order_date_week,
    DATE_TRUNC('month', o.order_date) AS order_date_month,
    DATE_TRUNC('quarter', o.order_date) AS order_date_quarter,
    DATE_TRUNC('year', o.order_date) AS order_date_year,
    
    -- Day of week for weekend/weekday analysis
    EXTRACT(DOW FROM o.order_date) AS day_of_week,
    EXTRACT(DAYOFYEAR FROM o.order_date) AS day_of_year,
    
    -- Order status
    o.status,
    
    -- Measures (additive numeric fields)
    o.total_amount,
    
    -- Line item counts
    COALESCE(oi.item_count, 0) AS item_count,
    COALESCE(oi.total_margin, 0) AS total_margin,
    
    -- Margin percentage (avoid division by zero)
    CASE 
        WHEN o.total_amount > 0 THEN 
            ROUND(COALESCE(oi.total_margin, 0) / o.total_amount * 100, 2)
        ELSE 0 
    END AS margin_percentage,
    
    -- Metadata
    o.updated_at,
    CURRENT_TIMESTAMP AS dbt_loaded_at

FROM {{ ref('stg_orders') }} o

-- Join to customer for denormalization
LEFT JOIN {{ ref('dim_customers') }} c 
    ON o.customer_id = c.customer_id

-- Join to aggregated order items for line item metrics
LEFT JOIN (
    SELECT 
        order_id,
        COUNT(*) AS item_count,
        SUM(line_total) AS total_line_revenue,
        SUM(gross_margin) AS total_margin
    FROM {{ ref('int_order_items') }}
    GROUP BY order_id
) oi ON o.order_id = oi.order_id

{% if is_incremental() %}
    -- Only process orders not already in the fact table
    -- This prevents duplicates on re-runs
    WHERE o.order_id NOT IN (SELECT order_id FROM {{ this }})
    
    -- Additionally, for late-arriving facts, check if order_date is recent
    -- This handles orders that arrive after the initial load
    AND o.order_date >= CURRENT_DATE - INTERVAL '30 days'
{% endif %}

-- Ensure positive order amounts (exclude refunds/credits processed as negatives)
WHERE o.total_amount > 0
