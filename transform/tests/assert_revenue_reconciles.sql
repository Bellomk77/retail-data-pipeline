-- Net revenue in the order fact table must equal net revenue computed line by line.
-- Returns rows (fails) if the two differ by more than one cent.
with lines as (select sum(gross_sales) - sum(return_amount) as net from {{ ref('int_order_lines') }}),
     orders as (select sum(net_revenue) as net from {{ ref('fct_orders') }})
select lines.net as line_net, orders.net as order_net
from lines, orders
where abs(lines.net - orders.net) > 0.01
