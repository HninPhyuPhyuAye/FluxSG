with ranked as (
    select
        *,
        row_number() over (
            partition by bus_stop_code
            order by ingested_at desc, snapshot_id desc
        ) as version_rank
    from {{ ref('stg_bus_stops') }}
)

select
    md5(bus_stop_code) as stop_key,
    bus_stop_code,
    road_name,
    description,
    latitude,
    longitude,
    snapshot_id as current_snapshot_id,
    ingested_at as source_ingested_at
from ranked
where version_rank = 1
