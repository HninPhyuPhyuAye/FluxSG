with latest_air as (
    select *
    from (
        select
            *,
            dense_rank() over (order by observed_at desc, snapshot_id desc) as snapshot_rank
        from {{ ref('stg_air_quality_regions') }}
    ) as ranked
    where snapshot_rank = 1
),

latest_weather as (
    select *
    from (
        select
            *,
            dense_rank() over (order by valid_from desc, snapshot_id desc) as snapshot_rank
        from {{ ref('stg_weather_forecasts') }}
    ) as ranked
    where snapshot_rank = 1
)

select
    md5(stop.stop_key || ':' || air.air_observation_key || ':' || weather.weather_observation_key)
        as stop_environment_key,
    stop.stop_key,
    stop.bus_stop_code,
    stop.description as bus_stop_description,
    stop.road_name,
    stop.latitude,
    stop.longitude,
    air.region as nearest_air_region,
    air.psi_24h,
    air.pm25_24h,
    air.pm25_1h,
    air.level as air_quality_level,
    air.haze_alert,
    air.observed_at as air_observed_at,
    weather.area as nearest_weather_area,
    weather.forecast,
    weather.valid_from as forecast_valid_from,
    weather.valid_to as forecast_valid_to,
    greatest(air.observed_at, weather.valid_from) as evaluated_at
from {{ ref('dim_bus_stops') }} as stop
cross join lateral (
    select *
    from latest_air
    order by
        power(stop.latitude - latest_air.latitude, 2)
        + power(stop.longitude - latest_air.longitude, 2)
    limit 1
) as air
cross join lateral (
    select *
    from latest_weather
    order by
        power(stop.latitude - latest_weather.latitude, 2)
        + power(stop.longitude - latest_weather.longitude, 2)
    limit 1
) as weather
