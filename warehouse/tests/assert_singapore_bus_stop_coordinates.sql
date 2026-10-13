select *
from {{ ref('dim_bus_stops') }}
where latitude not between 1.10 and 1.50
   or longitude not between 103.60 and 104.10
