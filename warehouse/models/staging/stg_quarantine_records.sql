select
    quarantine_id,
    dataset,
    object_key,
    source_name,
    record,
    record ->> 'reason' as rejection_reason,
    loaded_at
from {{ source('bronze', 'quarantine_records') }}
