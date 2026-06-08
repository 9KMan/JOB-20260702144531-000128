-- Intermediate Model: int_order_items
-- Purpose: Intermediate transformation layer that enriches order items with product cost
--          and calculates line-level and product-level metrics
-- Materialization: view (lightweight, recalculates on every query)
-- This model joins order items to product costs for margin calculations

{{ config(
    materialized='view',
    schema='intermediate',
    tags=['intermediate', 'order_items'],
    alias='int_order_items'
) }}

SELECT
    -- Primary key
    oi.order_item_id,
    
    -- Foreign keys
    oi.order_id,
    oi.product_id,
    
    -- Product details (snapshot at time of order)
    p.product_name,
    p.category,
    p.brand,
    
    -- Quantity and pricing
    oi.quantity,
    oi.unit_price,
    
    -- Line total (what customer paid)
    oi.quantity * oi.unit_price AS line_total,
    
    -- Cost and margin (from product catalog at time of order)
    p.cost AS unit_cost,
    oi.quantity * p.cost AS total_cost,
    
    -- Gross margin (revenue - cost)
    (oi.quantity * oi.unit_price) - (oi.quantity * p.cost) AS gross_margin,
    
    -- Margin percentage
    CASE 
        WHEN (oi.quantity * oi.unit_price) > 0 
        THEN ROUND(
            ((oi.quantity * oi.unit_price) - (oi.quantity * p.cost)) / 
            (oi.quantity * oi.unit_price) * 100, 
            2
        )
        ELSE 0 
    END AS gross_margin_percentage,
    
    -- Product-level aggregations (for later aggregation in fct_orders)
    1 AS item_record_count  -- Used for COUNT in downstream aggregations
    
FROM {{ source('ecom', 'order_items') }} oi

-- Join to products for cost data
-- Using LEFT JOIN because some products may have been discontinued
LEFT JOIN {{ source('ecom', 'products') }} p
    ON oi.product_id = p.product_id

-- Join to orders for date filtering and order validation
INNER JOIN {{ source('ecom', 'orders') }} o
    ON oi.order_id = o.order_id

-- Only include non-cancelled orders in margin calculations
WHERE o.status != 'cancelled'

-- Ensure positive quantities (returns show as negative, handled separately)
AND oi.quantity > 0

-- Ensure positive prices
AND oi.unit_price > 0
