with quarantine as (
    select dataset, count(*) as quarantined_record_count
    from {{ ref('stg_quarantine_records') }}
    group by dataset
)

select
    snapshot.dataset,
    count(*) as snapshot_count,
    max(snapshot.ingested_at) as latest_ingested_at,
    max(snapshot.loaded_at) as latest_loaded_at,
    round(
        extract(epoch from (current_timestamp - max(snapshot.ingested_at)))::numeric / 3600,
        2
    ) as freshness_hours,
    sum(snapshot.received_records) as total_received_records,
    sum(snapshot.valid_records) as total_valid_records,
    sum(snapshot.rejected_records) as total_rejected_records,
    coalesce(max(quarantine.quarantined_record_count), 0) as quarantined_record_count,
    round(
        sum(snapshot.valid_records)::numeric * 100
        / nullif(sum(snapshot.received_records), 0),
        2
    ) as completeness_percent,
    case
        when max(snapshot.ingested_at) < current_timestamp - interval '24 hours' then 'stale'
        when sum(snapshot.rejected_records) > 0 then 'degraded'
        else 'healthy'
    end as health_status
from {{ ref('stg_snapshots') }} as snapshot
left join quarantine using (dataset)
group by snapshot.dataset
