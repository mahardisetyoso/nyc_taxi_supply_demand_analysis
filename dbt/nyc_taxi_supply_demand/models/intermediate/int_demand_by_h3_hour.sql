{{ config(materialized='table') }}

-- Demand = pickup events per H3 cell per time bucket
-- Groups by h3_PICKUP_res8 intentionally

with trips as (
    select * from {{ ref('stg_yellow_trips') }}
)

select
    h3_pickup_res8              as h3_cell,
    day_of_week,
    hour_of_day,
    count(*)                    as demand_trips,
    round(avg(fare_amount), 2)  as avg_fare,
    round(avg(trip_distance), 2) as avg_distance
from trips
group by 1, 2, 3
