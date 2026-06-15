{{ config(materialized='table') }}

with gap_zones as (
    select * from {{ ref('mart_gap_zones') }}
),

zone_lookup as (
    select * from {{ ref('location_h3_zone_lookup') }}
),

-- Deduplicate: one H3 cell can overlap multiple TLC zones.
-- Take smallest location_id as the primary zone (D-053).
zone_primary as (
    select
        h3_res8,
        zone_name,
        borough,
        row_number() over (
            partition by h3_res8
            order by location_id asc
        ) as rn
    from zone_lookup
),

final as (
    select
        g.h3_cell,
        z.zone_name,
        z.borough,
        g.total_demand_trips,
        g.total_supply_trips,
        g.supply_demand_ratio,
        g.unmet_demand_rate,
        g.oversupply_ratio,
        g.zone_status,
        g.undersupply_frequency,
        g.active_time_buckets,
        g.gap_rank
    from gap_zones g
    left join zone_primary z
        on  g.h3_cell = z.h3_res8
        and z.rn = 1
)

select * from final
