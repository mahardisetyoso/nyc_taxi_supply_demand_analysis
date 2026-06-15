{{ config(materialized='table') }}

-- GRAIN: one row per (h3_cell × day_of_week × hour_of_day)
-- WARNING: bucket-level *_rate columns below are for time-of-day analysis ONLY.
-- DO NOT average them to summarize a zone — averaging ratios across buckets
-- where demand≈0 produces extreme outliers. Aggregate totals first, then divide.
-- (See mart_gap_zones for the correct zone-level rate computation.)

with demand as (
    select * from {{ ref('int_demand_by_h3_hour') }}
),

supply as (
    select * from {{ ref('int_supply_by_h3_hour') }}
),

joined as (
    select
        coalesce(d.h3_cell, s.h3_cell)              as h3_cell,
        coalesce(d.day_of_week, s.day_of_week)      as day_of_week,
        coalesce(d.hour_of_day, s.hour_of_day)      as hour_of_day,
        coalesce(d.demand_trips, 0)                  as demand_trips,
        coalesce(s.supply_trips, 0)                  as supply_trips,

        -- Absolute gap: positive = oversupplied, negative = undersupplied
        coalesce(s.supply_trips, 0)
            - coalesce(d.demand_trips, 0)            as supply_demand_gap,

        -- Bucket-level ratio (>1 oversupplied, <1 undersupplied).
        -- NULL when demand=0 (ratio undefined, not infinite).
        case
            when coalesce(d.demand_trips, 0) > 0
            then safe_divide(coalesce(s.supply_trips, 0), d.demand_trips)
        end                                          as bucket_supply_demand_ratio,

        -- Bucket-level unmet rate, clamped to [0,1].
        -- Negative (oversupply) clamped to 0: at bucket level we only care
        -- whether demand was met, not the magnitude of oversupply.
        -- NULL when demand=0.
        case
            when coalesce(d.demand_trips, 0) > 0
            then greatest(0.0, least(1.0,
                safe_divide(
                    d.demand_trips - coalesce(s.supply_trips, 0),
                    d.demand_trips
                )
            ))
        end                                          as bucket_unmet_demand_rate

    from demand d
    full outer join supply s
        on  d.h3_cell     = s.h3_cell
        and d.day_of_week = s.day_of_week
        and d.hour_of_day = s.hour_of_day
)

select * from joined
