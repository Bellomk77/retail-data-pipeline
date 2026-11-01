with source as (
    select * from {{ source('raw', 'customers') }}
)
select
    cast(customer_id as integer)        as customer_id,
    trim(first_name)                    as first_name,
    trim(last_name)                     as last_name,
    lower(trim(email))                  as email,        -- fixes "  AMARA.SMITH1@EXAMPLE.COM "
    upper(trim(province))               as province,     -- fixes " on" -> "ON"
    cast(signup_date as date)           as signup_date
from source
qualify row_number() over (partition by customer_id order by _loaded_at desc) = 1
