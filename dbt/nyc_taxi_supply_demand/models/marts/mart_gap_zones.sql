{{ config(materialized='table') }}

with gap as (
    select * from {{ ref('int_supply_demand_gap') }}
),

-- Aggregate TOTALS first, then compute rates from totals.
-- This is "rate of totals", NOT "average of rates" — robust to sparse buckets.
zone_totals as (
    select
        h3_cell,
        sum(demand_trips)                            as total_demand_trips,
        sum(supply_trips)                            as total_supply_trips,
        count(*)                                     as active_time_buckets,
        countif(supply_trips < demand_trips)         as undersupplied_buckets
    from gap
    group by h3_cell
),

-- Minimum 500 demand trips/year to exclude statistical noise.
significant_zones as (
    select * from zone_totals
    where total_demand_trips >= 500
),

zone_metrics as (
    select
        h3_cell,
        total_demand_trips,
        total_supply_trips,

        -- Zone-level supply/demand ratio from totals.
        -- >1 oversupplied, <1 undersupplied, =1 balanced.
        round(safe_divide(total_supply_trips, total_demand_trips), 4)
            as supply_demand_ratio,

        -- Unmet demand rate from totals, clamped [0,1].
        -- Only positive when demand > supply (genuine shortfall).
        round(greatest(0.0, least(1.0,
            safe_divide(
                total_demand_trips - total_supply_trips,
                total_demand_trips
            )
        )), 4)                                        as unmet_demand_rate,

        -- Oversupply ratio: how many extra supply units per demand unit.
        -- 0 when undersupplied/balanced. Separate metric, separate meaning.
        round(greatest(0.0,
            safe_divide(
                total_supply_trips - total_demand_trips,
                total_demand_trips
            )
        ), 4)                                         as oversupply_ratio,

        -- Share of time-buckets that were undersupplied.
        round(safe_divide(undersupplied_buckets, active_time_buckets), 4)
            as undersupply_frequency,

        active_time_buckets,
        undersupplied_buckets
    from significant_zones
),

classified as (
    select
        *,
        -- Three-way classification with justified thresholds.
        -- BALANCED band = ±10% (ratio 0.9–1.1) — standard ops tolerance
        -- for supply matching demand. Outside it = action needed.
        case
            when supply_demand_ratio < 0.9  then 'UNDERSUPPLIED'
            when supply_demand_ratio > 1.1  then 'OVERSUPPLIED'
            else 'BALANCED'
        end                                           as zone_status
    from zone_metrics
),

ranked as (
    select
        *,
        rank() over (
            order by unmet_demand_rate desc, total_demand_trips desc
        )                                             as gap_rank
    from classified
)

select * from ranked
