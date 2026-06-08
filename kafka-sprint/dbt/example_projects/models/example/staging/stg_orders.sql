-- Staging Model: stg_orders
-- Purpose: Clean and standardize raw orders data from ecom source
-- Materialization: view (lightweight, always reflects latest source data)
-- This is the first transformation layer - maps 1:1 with source table

{{ config(
    materialized='view',
    schema='staging',
    tags=['staging', 'orders'],
    alias='stg_orders'
) }}

SELECT
    -- Primary key
    o.order_id,
    
    -- Foreign keys
    o.customer_id,
    
    -- Core business fields
    o.order_date,
    o.status,
    o.total_amount,
    
    -- Address field (may be NULL for digital products)
    o.shipping_address,
    
    -- Metadata fields
    o.updated_at,
    o.loaded_at,
    
    -- Cleaned/transformation fields
    -- Convert status to lowercase for consistency
    LOWER(o.status) AS status_raw,
    
    -- Extract date parts for easier filtering
    DATE_TRUNC('day', o.order_date) AS order_date_day,
    DATE_TRUNC('week', o.order_date) AS order_date_week,
    DATE_TRUNC('month', o.order_date) AS order_date_month,
    DATE_TRUNC('year', o.order_date) AS order_date_year,
    
    -- Flag for recent orders (useful for filtering)
    CASE 
        WHEN o.order_date >= CURRENT_DATE - INTERVAL '7 days' THEN TRUE 
        ELSE FALSE 
    END AS is_recent
    
FROM {{ source('ecom', 'orders') }} o

-- Data quality filters (optional but recommended)
WHERE 
    -- Exclude test orders
    o.order_id NOT LIKE 'TEST-%'
    AND o.order_id NOT LIKE '%_test'
    
    -- Ensure we have a valid order
    AND o.order_id IS NOT NULL
    AND o.order_id != ''
    
    -- Ensure positive amounts (can indicate refunds processed as separate transactions)
    AND o.total_amount >= 0
