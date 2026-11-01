select
    order_date,
    channel,
    count(*) filter (where status != 'cancelled')   as orders,
    sum(gross_sales)                                 as gross_sales,
    sum(return_amount)                               as return_amount,
    sum(net_revenue)                                 as net_revenue
from {{ ref('fct_orders') }}
group by all
