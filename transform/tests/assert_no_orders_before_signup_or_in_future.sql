select o.order_id, o.order_date, c.signup_date
from {{ ref('fct_orders') }} o
join {{ ref('dim_customers') }} c using (customer_id)
where o.order_date < c.signup_date or o.order_date > current_date
