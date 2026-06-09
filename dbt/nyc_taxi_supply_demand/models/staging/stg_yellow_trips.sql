{{ config(materialized='view') }}

with source as (
    select * from {{ source('geoops_raw', 'yellow_trips_h3_enriched') }}
),

cleaned as (
    select
        -- H3 spatial keys
        h3_pickup_res8,
        h3_dropoff_res8,

        -- Time dimensions (pre-computed by PySpark Flow 4)
        day_of_week,      -- 0=Monday, 6=Sunday
        hour_of_day,      -- 0-23

        -- Location IDs
        PULocationID        as pu_location_id,
        DOLocationID        as do_location_id,

        -- Trip metrics
        trip_distance,
        fare_amount,
        tip_amount,
        total_amount,

        -- Timestamps
        tpep_pickup_datetime    as pickup_datetime,
        tpep_dropoff_datetime   as dropoff_datetime

    from source
    where h3_pickup_res8 is not null
      and h3_dropoff_res8 is not null
)

select * from cleaned
