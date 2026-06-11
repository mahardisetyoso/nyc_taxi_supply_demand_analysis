{{
    config(
        materialized='table'
    )
}}

with gap_zones as (
    select * from {{ ref('mart_gap_zones_named') }}
),

classified as (
    select
        h3_cell,
        zone_name,
        borough,
        total_demand_trips,
        total_supply_trips,
        avg_unmet_demand_rate,
        avg_supply_demand_ratio,
        gap_rank,

        case
            when avg_unmet_demand_rate > 0 then 'UNDERSUPPLIED'
            when avg_unmet_demand_rate < -5 then 'HEAVILY_OVERSUPPLIED'
            else 'BALANCED'
        end as zone_status,

        -- Revenue loss hanya untuk undersupplied zones
        case
            when avg_unmet_demand_rate > 0
            then round(total_demand_trips * avg_unmet_demand_rate * 18.50, 2)
            else 0
        end as estimated_revenue_loss_usd,

        case
            when avg_unmet_demand_rate > 0
            then round(total_demand_trips * avg_unmet_demand_rate)
            else 0
        end as estimated_unmet_trips

    from gap_zones
)

select
    *,
    sum(estimated_revenue_loss_usd) over () as total_revenue_loss_usd
from classified
order by estimated_revenue_loss_usd desc
