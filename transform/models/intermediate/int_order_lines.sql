-- One row per order line, enriched with order and product context.
-- Business rules:
--   * cancelled orders carry no revenue
--   * returns (negative quantities) reduce net revenue
--   * lines whose product is missing from the catalogue are kept and flagged, not dropped,
--     so revenue still reconciles to the source
select
    i.order_line_id,
    i.order_id,
    o.customer_id,
    o.order_date,
    o.channel,
    o.status,
    i.product_id,
    coalesce(p.product_name, 'Unknown product') as product_name,
    coalesce(p.category, 'Unknown')             as category,
    p.product_id is null                        as is_orphan_product,
    i.quantity,
    i.unit_price,
    i.is_return,
    case when o.status = 'cancelled' then 0
         when not i.is_return then i.line_amount else 0 end      as gross_sales,
    case when o.status = 'cancelled' then 0
         when i.is_return then -i.line_amount else 0 end         as return_amount
from {{ ref('stg_order_items') }} i
join {{ ref('stg_orders') }} o using (order_id)
left join {{ ref('stg_products') }} p using (product_id)
