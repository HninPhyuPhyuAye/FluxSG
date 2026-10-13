with ordered as (
    select
        *,
        lag(distance_km) over (
            partition by service_no, direction
            order by stop_sequence
        ) as previous_distance_km
    from {{ ref('fct_bus_route_stops') }}
)

select *
from ordered
where stop_sequence < 1
   or distance_km < 0
   or distance_km < previous_distance_km
