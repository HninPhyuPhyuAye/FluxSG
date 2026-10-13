select
    md5(snapshot.snapshot_id || ':' || (region ->> 'region')) as air_observation_key,
    snapshot.snapshot_id,
    snapshot.object_key,
    snapshot.ingested_at,
    (snapshot.payload ->> 'observed_at')::timestamptz as observed_at,
    (snapshot.payload ->> 'updated_at')::timestamptz as updated_at,
    (snapshot.payload ->> 'national_psi')::integer as national_psi,
    snapshot.payload ->> 'national_level' as national_level,
    (snapshot.payload ->> 'haze_alert')::boolean as haze_alert,
    region ->> 'region' as region,
    (region ->> 'latitude')::double precision as latitude,
    (region ->> 'longitude')::double precision as longitude,
    (region ->> 'psi_24h')::integer as psi_24h,
    (region ->> 'pm25_24h')::integer as pm25_24h,
    (region ->> 'pm25_1h')::integer as pm25_1h,
    region ->> 'level' as level
from {{ source('bronze', 'raw_snapshots') }} as snapshot
cross join lateral jsonb_array_elements(snapshot.payload -> 'regions') as region
where snapshot.dataset = 'air_quality'
