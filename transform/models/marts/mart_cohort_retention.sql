-- Monthly cohort retention: of the customers who first ordered in month M,
-- what share ordered again N months later?
with firsts as (
    select customer_id, date_trunc('month', min(order_date)) as cohort_month
    from {{ ref('fct_orders') }}
    where customer_id is not null and status != 'cancelled'
    group by customer_id
),
activity as (
    select distinct f.customer_id, f.cohort_month,
           date_diff('month', f.cohort_month, date_trunc('month', o.order_date)) as months_since_first
    from {{ ref('fct_orders') }} o
    join firsts f using (customer_id)
    where o.status != 'cancelled'
),
sizes as (
    select cohort_month, count(*) as cohort_size from firsts group by cohort_month
)
select
    a.cohort_month,
    a.months_since_first,
    count(*)                                         as active_customers,
    s.cohort_size,
    round(count(*) / s.cohort_size, 4)               as retention_rate
from activity a
join sizes s using (cohort_month)
group by a.cohort_month, a.months_since_first, s.cohort_size
order by 1, 2
