# Data sources

## NEA two-hour weather forecast

- Provider: data.gov.sg / National Environment Agency
- Endpoint: `https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast`
- Authentication: none
- Current use: live source for the Milestone 1 vertical slice
- Quality checks: non-empty areas, known coordinates, forecast text, source
  timestamp, API status code

## LTA DataMall

- Provider: Land Transport Authority
- Authentication: account key required
- Planned datasets: bus stops, bus routes, bus arrival, passenger volume, and
  traffic speed bands where licence and retention conditions permit
- Current use: configuration-readiness check only

## NEA PSI and PM2.5 readings

- Provider: data.gov.sg / National Environment Agency
- Endpoints: `/v2/real-time/api/psi` and `/v2/real-time/api/pm25`
- Authentication: none
- Current use: five-region 24-hour PSI, 24-hour PM2.5, and one-hour PM2.5
- Quality checks: five expected regions, coordinates, all three readings,
  observation and update timestamps, API status codes
- Presentation: the highest regional 24-hour PSI drives the national alert band;
  each regional value remains visible so the user can make a local decision

PSI bands follow Singapore's official categories: Good (0-50), Moderate
(51-100), Unhealthy (101-200), Very Unhealthy (201-300), and Hazardous
(above 300). Citizen guidance links to `haze.gov.sg`; FluxSG does not replace
official health, school, workplace, or medical advice.

Before persisting any LTA dataset, its current licence, rate limits, retention
conditions, and attribution requirements will be recorded here.

## Data governance

- No personal data is needed or intentionally collected.
- Every stored record will include source and ingestion timestamps.
- Rejected records will be quarantined with a machine-readable reason.
- Raw, cleaned, and analytical datasets will have separate schemas and access
  policies.

