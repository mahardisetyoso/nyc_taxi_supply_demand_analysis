{{ config(materialized='table') }}

with gap_zones as (
    select * from {{ ref('mart_gap_zones_named') }}
),

revenue as (
    select
        h3_cell,
        zone_name,
        borough,
        total_demand_trips,
        total_supply_trips,
        supply_demand_ratio,
        unmet_demand_rate,
        oversupply_ratio,
        zone_status,
        gap_rank,

        -- Revenue loss ONLY for UNDERSUPPLIED zones (genuine supply gap).
        -- BALANCED zones may have slight unmet_demand_rate > 0 but are
        -- within ±10% tolerance — not actionable, not counted as loss.
        -- $18.50 = avg NYC yellow taxi fare (TLC 2023). Lower-bound estimate.
        case
            when zone_status = 'UNDERSUPPLIED'
            then round(total_demand_trips * unmet_demand_rate * 18.50, 2)
            else 0
        end                                           as estimated_revenue_loss_usd,

        case
            when zone_status = 'UNDERSUPPLIED'
            then round(total_demand_trips * unmet_demand_rate)
            else 0
        end                                           as estimated_unmet_trips

    from gap_zones
)

select
    *,
    sum(estimated_revenue_loss_usd) over ()           as total_revenue_loss_usd
from revenue
order by estimated_revenue_loss_usd desc
