{# Turn exported text like "$1,299.00" into a number. #}
{% macro parse_money(column) -%}
    cast(replace(replace(trim({{ column }}), '$', ''), ',', '') as decimal(12, 2))
{%- endmacro %}
