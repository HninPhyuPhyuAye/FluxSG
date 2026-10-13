select
    service_no,
    direction,
    operator,
    stop_count,
    average_psi_24h,
    maximum_psi_24h,
    average_pm25_1h,
    maximum_pm25_1h,
    unhealthy_stop_count
from {{ ref('mart_service_environment_risk') }}
order by average_psi_24h desc, average_pm25_1h desc, service_no
limit 10
