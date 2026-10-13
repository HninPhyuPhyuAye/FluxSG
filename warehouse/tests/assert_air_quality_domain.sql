select *
from {{ ref('stg_air_quality_regions') }}
where psi_24h < 0
   or pm25_24h < 0
   or pm25_1h < 0
   or latitude not between 1.10 and 1.50
   or longitude not between 103.60 and 104.10
