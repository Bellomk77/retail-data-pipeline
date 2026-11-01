select
    cast(order_line_id as bigint)                     as order_line_id,
    cast(order_id as bigint)                          as order_id,
    cast(product_id as integer)                       as product_id,
    cast(quantity as integer)                         as quantity,
    {{ parse_money('unit_price') }}                   as unit_price,
    cast(quantity as integer) < 0                     as is_return,
    cast(quantity as integer) * {{ parse_money('unit_price') }} as line_amount
from {{ source('raw', 'order_items') }}
