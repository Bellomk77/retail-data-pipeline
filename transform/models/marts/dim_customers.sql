with orders as (
    select
        customer_id,
        min(order_date)                                  as first_order_date,
        max(order_date)                                  as last_order_date,
        count(*) filter (where status != 'cancelled')    as lifetime_orders,
        sum(net_revenue)                                 as lifetime_net_revenue
    from {{ ref('fct_orders') }}
    where customer_id is not null
    group by customer_id
),
ranked as (
    select *, percent_rank() over (order by lifetime_net_revenue) as ltv_percentile
    from orders
)
select
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.province,
    c.signup_date,
    r.first_order_date,
    r.last_order_date,
    coalesce(r.lifetime_orders, 0)                       as lifetime_orders,
    coalesce(r.lifetime_net_revenue, 0)                  as lifetime_net_revenue,
    case
        when r.customer_id is null        then 'Prospect'
        when r.ltv_percentile >= 0.95     then 'VIP'
        when r.lifetime_orders >= 2       then 'Repeat'
        else 'One-time'
    end                                                  as customer_segment
from {{ ref('stg_customers') }} c
left join ranked r using (customer_id)
