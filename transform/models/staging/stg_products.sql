select
    cast(product_id as integer)           as product_id,
    trim(product_name)                    as product_name,
    trim(category)                        as category,
    {{ parse_money('list_price') }}       as list_price
from {{ source('raw', 'products') }}
