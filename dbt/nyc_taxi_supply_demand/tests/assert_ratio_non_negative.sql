-- Fails if any supply_demand_ratio is negative
select h3_cell, supply_demand_ratio
from {{ ref('mart_gap_zones') }}
where supply_demand_ratio < 0
