{{ config(materialized='incremental', unique_key='order_id', incremental_strategy='delete+insert') }}

-- Order-grain fact table. Incremental: each run reprocesses a 3-day lookback window
-- so late-arriving lines and status changes are picked up without a full rebuild.
select
    order_id,
    any_value(customer_id)                     as customer_id,
    any_value(order_date)                      as order_date,
    any_value(channel)                         as channel,
    any_value(status)                          as status,
    count(*)                                   as line_count,
    sum(case when not is_return then quantity else 0 end) as units_sold,
    sum(gross_sales)                           as gross_sales,
    sum(return_amount)                         as return_amount,
    sum(gross_sales) - sum(return_amount)      as net_revenue,
    bool_or(is_orphan_product)                 as has_orphan_product
from {{ ref('int_order_lines') }}
{% if is_incremental() %}
where order_date >= (select max(order_date) - interval 3 day from {{ this }})
{% endif %}
group by order_id
