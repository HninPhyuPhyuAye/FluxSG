select *
from {{ ref('stg_snapshots') }}
where valid_records + rejected_records > received_records
   or completeness_percent not between 0 and 100
