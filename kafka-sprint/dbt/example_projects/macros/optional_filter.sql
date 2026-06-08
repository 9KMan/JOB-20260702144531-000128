{# 
    Macro: optional_filter
    
    Purpose: Conditionally add a WHERE clause filter based on a runtime condition.
             This is useful when you want to make filters configurable without duplicating SQL.
    
    Usage:
        SELECT * 
        FROM {{ ref('orders') }}
        WHERE 1=1
        {{ optional_filter('status', '=', "'shipped'", var('filter_shipped', false)) }}
    
    Parameters:
        column_name: The column to filter on (string)
        operator: SQL operator (string, e.g., '=', '!=', '>', '<', 'IN')
        value: The value to compare against (string, including quotes for literals)
        condition: Boolean Jinja expression that controls whether filter is applied
#}

{% macro optional_filter(column_name, operator, value, condition) %}
    {% if condition %}
        AND {{ column_name }} {{ operator }} {{ value }}
    {% endif %}
{% endmacro %}

{# 
    Macro: optional_filter_or
    
    Purpose: Same as optional_filter but uses OR instead of AND
    
    Usage:
        WHERE status = 'shipped'
        {{ optional_filter_or('region', '=', "'US'", var('filter_us', false)) }}
#}

{% macro optional_filter_or(column_name, operator, value, condition) %}
    {% if condition %}
        OR {{ column_name }} {{ operator }} {{ value }}
    {% endif %}
{% endmacro %}

{#
    Macro: date_range_filter
    
    Purpose: Apply a date range filter conditionally
    
    Usage:
        {{ date_range_filter('order_date', var('start_date'), var('end_date'), var('apply_filter', false)) }}
#}

{% macro date_range_filter(column_name, start_date, end_date, apply_filter) %}
    {% if apply_filter %}
        AND {{ column_name }} >= {{ start_date }}
        AND {{ column_name }} <= {{ end_date }}
    {% endif %}
{% endmacro %}

{#
    Macro: get_where_clause
    
    Purpose: Build a WHERE clause dynamically based on a dict of conditions
    
    Usage:
        {% set conditions = {
            'status': 'shipped',
            'customer_tier': 'gold'
        } %}
        WHERE 1=1
        {{ get_where_clause(conditions) }}
#}

{% macro get_where_clause(conditions) %}
    {% for column, value in conditions.items() %}
        AND {{ column }} = '{{ value }}'
    {% endfor %}
{% endmacro %}

{#
    Macro: pivot_column
    
    Purpose: Generate pivot aggregation for a column with multiple values
    
    Usage:
        {{ pivot_column('status', ['pending', 'shipped', 'delivered'], 'count') }}
#}

{% macro pivot_column(column, values, aggregation) %}
    {% for value in values %}
        {{ aggregation }}(CASE WHEN {{ column }} = '{{ value }}' THEN 1 ELSE 0 END) AS {{ column }}_{{ value }}
        {% if not loop.last %},{% endif %}
    {% endfor %}
{% endmacro %}
