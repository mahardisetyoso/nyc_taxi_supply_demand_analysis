-- Fails if any unmet_demand_rate is outside [0, 1]
select h3_cell, unmet_demand_rate
from {{ ref('mart_gap_zones') }}
where unmet_demand_rate < 0 or unmet_demand_rate > 1
