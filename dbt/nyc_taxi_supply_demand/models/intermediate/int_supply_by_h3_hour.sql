{{ config(materialized='table') }}

-- Supply proxy = dropoff events per H3 cell per time bucket
-- Groups by h3_DROPOFF_res8 intentionally
-- Dropoff = point where taxi becomes available for next trip

with trips as (
    select * from {{ ref('stg_yellow_trips') }}
)

select
    h3_dropoff_res8             as h3_cell,
    day_of_week,
    hour_of_day,
    count(*)                    as supply_trips
from trips
group by 1, 2, 3
