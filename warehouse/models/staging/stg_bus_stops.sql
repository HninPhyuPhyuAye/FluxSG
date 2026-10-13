select
    md5(snapshot.snapshot_id || ':' || (stop ->> 'BusStopCode')) as bus_stop_version_key,
    snapshot.snapshot_id,
    snapshot.object_key,
    snapshot.ingested_at,
    stop ->> 'BusStopCode' as bus_stop_code,
    stop ->> 'RoadName' as road_name,
    stop ->> 'Description' as description,
    (stop ->> 'Latitude')::double precision as latitude,
    (stop ->> 'Longitude')::double precision as longitude
from {{ source('bronze', 'raw_snapshots') }} as snapshot
cross join lateral jsonb_array_elements(
    snapshot.payload -> 'datasets' -> 'bus_stops' -> 'records'
) as stop
where snapshot.dataset = 'lta_transport_network'
