{{ config(materialized='table') }}

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

        -- Absolute gap: negative = undersupplied
        coalesce(s.supply_trips, 0)
            - coalesce(d.demand_trips, 0)            as supply_demand_gap,

        -- Ratio: <1.0 = undersupplied, >1.0 = oversupplied
        safe_divide(
            coalesce(s.supply_trips, 0),
            coalesce(d.demand_trips, 0)
        )                                            as supply_demand_ratio,

        -- Unmet demand rate: % of demand not covered by supply
        safe_divide(
            coalesce(d.demand_trips, 0)
                - coalesce(s.supply_trips, 0),
            coalesce(d.demand_trips, 0)
        )                                            as unmet_demand_rate

    from demand d
    full outer join supply s
        on  d.h3_cell     = s.h3_cell
        and d.day_of_week = s.day_of_week
        and d.hour_of_day = s.hour_of_day
)

select * from joined
