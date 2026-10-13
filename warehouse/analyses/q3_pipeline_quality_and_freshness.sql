select
    dataset,
    snapshot_count,
    freshness_hours,
    completeness_percent,
    total_rejected_records,
    quarantined_record_count,
    health_status
from {{ ref('mart_ingestion_health') }}
order by health_status desc, completeness_percent, dataset
