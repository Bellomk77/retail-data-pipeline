-- Removes exact duplicate rows created when an export was re-sent.
with source as (
    select * from {{ source('raw', 'orders') }}
),
deduplicated as (
    select *
    from source
    qualify row_number() over (partition by order_id order by _loaded_at) = 1
)
select
    cast(order_id as bigint)                         as order_id,
    cast(nullif(trim(customer_id), '') as integer)   as customer_id,
    nullif(trim(customer_id), '') is null            as is_guest_checkout,
    cast(ordered_at as timestamp)                    as ordered_at,
    cast(ordered_at as date)                         as order_date,
    lower(trim(channel))                             as channel,
    lower(trim(status))                              as status
from deduplicated
