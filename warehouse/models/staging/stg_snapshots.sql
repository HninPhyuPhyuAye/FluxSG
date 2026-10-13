select
    snapshot_id,
    dataset,
    object_key,
    source_name,
    ingested_at,
    source_updated_at,
    received_records,
    valid_records,
    rejected_records,
    round(valid_records::numeric * 100 / nullif(received_records, 0), 2) as completeness_percent,
    loaded_at
from {{ source('bronze', 'raw_snapshots') }}
where dataset in ('weather_outlook', 'air_quality', 'lta_transport_network')
