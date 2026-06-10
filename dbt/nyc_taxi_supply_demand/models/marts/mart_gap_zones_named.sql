{{
    config(
        materialized='table'
    )
}}

with gap_zones as (
    select * from {{ ref('mart_gap_zones') }}
),

zone_lookup as (
    select * from {{ ref('location_h3_zone_lookup') }}
),

-- Deduplicate: satu H3 cell bisa overlap multiple TLC zones
-- Ambil zone dengan location_id terkecil sebagai primary zone
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
        g.avg_supply_demand_ratio,
        g.avg_unmet_demand_rate,
        g.undersupply_frequency,
        g.gap_rank
    from gap_zones g
    left join zone_primary z
        on g.h3_cell = z.h3_res8
        and z.rn = 1
)

select * from final
