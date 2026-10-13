select
    bus_stop_code,
    bus_stop_description,
    road_name,
    nearest_air_region,
    psi_24h,
    pm25_1h,
    nearest_weather_area,
    forecast
from {{ ref('mart_bus_stop_environment') }}
where haze_alert
order by psi_24h desc, pm25_1h desc, bus_stop_code
limit 20
