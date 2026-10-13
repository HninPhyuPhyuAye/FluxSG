with latest_snapshot as (
    select snapshot_id
    from {{ ref('stg_bus_routes') }}
    order by ingested_at desc, snapshot_id desc
    limit 1
)

select
    md5(route.service_no || ':' || route.direction || ':' || route.stop_sequence) as route_stop_key,
    md5(route.service_no || ':' || route.direction) as service_key,
    md5(route.bus_stop_code) as stop_key,
    route.service_no,
    route.direction,
    route.operator,
    route.stop_sequence,
    route.bus_stop_code,
    route.distance_km,
    route.weekday_first_bus,
    route.weekday_last_bus,
    route.saturday_first_bus,
    route.saturday_last_bus,
    route.sunday_first_bus,
    route.sunday_last_bus,
    route.snapshot_id as current_snapshot_id,
    route.ingested_at as source_ingested_at
from {{ ref('stg_bus_routes') }} as route
inner join latest_snapshot using (snapshot_id)
