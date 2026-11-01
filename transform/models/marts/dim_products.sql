select
    p.product_id,
    p.product_name,
    p.category,
    p.list_price,
    coalesce(sum(l.gross_sales), 0)                    as gross_sales,
    coalesce(sum(case when l.is_return then -l.quantity end), 0) as units_returned,
    coalesce(sum(case when not l.is_return then l.quantity end), 0) as units_sold,
    round(coalesce(sum(case when l.is_return then -l.quantity end), 0)
          / nullif(sum(case when not l.is_return then l.quantity end), 0), 4) as return_rate
from {{ ref('stg_products') }} p
left join {{ ref('int_order_lines') }} l using (product_id)
group by all
