select
    route.service_key,
    route.service_no,
    route.direction,
    route.operator,
    count(distinct route.stop_key) as stop_count,
    round(avg(environment.psi_24h)::numeric, 1) as average_psi_24h,
    max(environment.psi_24h) as maximum_psi_24h,
    round(avg(environment.pm25_1h)::numeric, 1) as average_pm25_1h,
    max(environment.pm25_1h) as maximum_pm25_1h,
    count(distinct route.stop_key) filter (
        where environment.air_quality_level in ('Unhealthy', 'Very Unhealthy', 'Hazardous')
    ) as unhealthy_stop_count,
    bool_or(environment.haze_alert) as haze_alert,
    max(environment.evaluated_at) as evaluated_at
from {{ ref('fct_bus_route_stops') }} as route
inner join {{ ref('mart_bus_stop_environment') }} as environment using (stop_key)
group by route.service_key, route.service_no, route.direction, route.operator
