{{ config(materialized='table') }}

with gap as (
    select * from {{ ref('int_supply_demand_gap') }}
)

select
    day_of_week,
    hour_of_day,
    sum(demand_trips)                                         as total_demand_trips,
    sum(supply_trips)                                         as total_supply_trips,
    round(avg(supply_demand_ratio), 4)                        as avg_supply_demand_ratio,
    approx_quantiles(supply_demand_ratio, 2)[offset(1)]       as median_supply_demand_ratio,
    countif(supply_demand_ratio < 1.0)                        as undersupplied_cell_count,
    count(distinct h3_cell)                                   as active_cell_count,
    round(
        safe_divide(
            countif(supply_demand_ratio < 1.0),
            count(distinct h3_cell)
        ), 4
    )                                                         as undersupply_cell_rate
from gap
where demand_trips > 0
group by day_of_week, hour_of_day
order by day_of_week, hour_of_day
