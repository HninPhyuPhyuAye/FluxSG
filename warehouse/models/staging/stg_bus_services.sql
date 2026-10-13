select
    md5(
        snapshot.snapshot_id || ':' || (service ->> 'ServiceNo') || ':'
        || (service ->> 'Direction')
    ) as bus_service_version_key,
    snapshot.snapshot_id,
    snapshot.object_key,
    snapshot.ingested_at,
    service ->> 'ServiceNo' as service_no,
    (service ->> 'Direction')::integer as direction,
    service ->> 'Operator' as operator,
    service ->> 'Category' as category,
    service ->> 'OriginCode' as origin_code,
    service ->> 'DestinationCode' as destination_code,
    nullif(service ->> 'LoopDesc', '') as loop_description,
    service ->> 'AM_Peak_Freq' as am_peak_frequency,
    service ->> 'AM_Offpeak_Freq' as am_offpeak_frequency,
    service ->> 'PM_Peak_Freq' as pm_peak_frequency,
    service ->> 'PM_Offpeak_Freq' as pm_offpeak_frequency
from {{ source('bronze', 'raw_snapshots') }} as snapshot
cross join lateral jsonb_array_elements(
    snapshot.payload -> 'datasets' -> 'bus_services' -> 'records'
) as service
where snapshot.dataset = 'lta_transport_network'
