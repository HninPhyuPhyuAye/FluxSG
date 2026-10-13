select
    md5(snapshot.snapshot_id || ':' || (forecast ->> 'area')) as weather_observation_key,
    snapshot.snapshot_id,
    snapshot.object_key,
    snapshot.ingested_at,
    (snapshot.payload ->> 'source_updated_at')::timestamptz as source_updated_at,
    (snapshot.payload ->> 'valid_from')::timestamptz as valid_from,
    (snapshot.payload ->> 'valid_to')::timestamptz as valid_to,
    forecast ->> 'area' as area,
    forecast ->> 'forecast' as forecast,
    (forecast ->> 'latitude')::double precision as latitude,
    (forecast ->> 'longitude')::double precision as longitude
from {{ source('bronze', 'raw_snapshots') }} as snapshot
cross join lateral jsonb_array_elements(snapshot.payload -> 'forecasts') as forecast
where snapshot.dataset = 'weather_outlook'
