select
    md5(
        snapshot.snapshot_id || ':' || (route ->> 'ServiceNo') || ':'
        || (route ->> 'Direction') || ':' || (route ->> 'StopSequence')
    ) as route_stop_version_key,
    snapshot.snapshot_id,
    snapshot.object_key,
    snapshot.ingested_at,
    route ->> 'ServiceNo' as service_no,
    (route ->> 'Direction')::integer as direction,
    route ->> 'Operator' as operator,
    (route ->> 'StopSequence')::integer as stop_sequence,
    route ->> 'BusStopCode' as bus_stop_code,
    (route ->> 'Distance')::numeric(8, 2) as distance_km,
    route ->> 'WD_FirstBus' as weekday_first_bus,
    route ->> 'WD_LastBus' as weekday_last_bus,
    route ->> 'SAT_FirstBus' as saturday_first_bus,
    route ->> 'SAT_LastBus' as saturday_last_bus,
    route ->> 'SUN_FirstBus' as sunday_first_bus,
    route ->> 'SUN_LastBus' as sunday_last_bus
from {{ source('bronze', 'raw_snapshots') }} as snapshot
cross join lateral jsonb_array_elements(
    snapshot.payload -> 'datasets' -> 'bus_routes' -> 'records'
) as route
where snapshot.dataset = 'lta_transport_network'
