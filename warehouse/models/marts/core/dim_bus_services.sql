with ranked as (
    select
        *,
        row_number() over (
            partition by service_no, direction
            order by ingested_at desc, snapshot_id desc
        ) as version_rank
    from {{ ref('stg_bus_services') }}
)

select
    md5(service_no || ':' || direction) as service_key,
    service_no,
    direction,
    operator,
    category,
    origin_code,
    destination_code,
    loop_description,
    am_peak_frequency,
    am_offpeak_frequency,
    pm_peak_frequency,
    pm_offpeak_frequency,
    snapshot_id as current_snapshot_id,
    ingested_at as source_ingested_at
from ranked
where version_rank = 1
