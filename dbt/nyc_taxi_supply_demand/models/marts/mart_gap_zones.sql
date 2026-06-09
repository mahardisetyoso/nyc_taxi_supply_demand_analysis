{{ config(materialized='table') }}

with gap as (
    select * from {{ ref('int_supply_demand_gap') }}
),

zone_summary as (
    select
        h3_cell,
        approx_quantiles(supply_demand_ratio, 2)[offset(1)]   as median_supply_demand_ratio,
        round(avg(supply_demand_ratio), 4)                    as avg_supply_demand_ratio,
        round(avg(unmet_demand_rate), 4)                      as avg_unmet_demand_rate,
        sum(demand_trips)                                     as total_demand_trips,
        sum(supply_trips)                                     as total_supply_trips,
        round(avg(demand_trips), 1)                           as avg_hourly_demand,
        round(avg(supply_trips), 1)                           as avg_hourly_supply,
        count(*)                                              as active_time_buckets,
        countif(supply_demand_ratio < 1.0)                    as undersupplied_buckets,
        round(
            safe_divide(
                countif(supply_demand_ratio < 1.0),
                count(*)
            ), 4
        )                                                     as undersupply_frequency
    from gap
    where demand_trips > 0
    group by h3_cell
),

-- Filter: minimum 500 demand trips to exclude statistical noise
-- Low-volume cells (< 500 trips/year) produce misleading unmet_demand_rate
significant_zones as (
    select * from zone_summary
    where total_demand_trips >= 500
),

ranked as (
    select
        *,
        rank() over (
            order by avg_unmet_demand_rate desc nulls last
        )                                                     as gap_rank
    from significant_zones
)

select * from ranked
