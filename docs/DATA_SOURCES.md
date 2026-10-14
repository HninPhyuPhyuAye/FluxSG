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
- Current datasets: bus stops, bus services, bus routes, and Bus Arrival v3
- Current use: network summary, stop search, scheduled routes, and live
  next-three-bus arrival boards
- Quality checks: bounded 500-record pagination, schema validation, five-digit
  stop codes, valid coordinates, arrival timestamps, and rejected-record reasons
- Cache policy: ad-hoc stop/service/route metadata is cached for six hours;
  live arrivals are requested on demand
- Security: `AccountKey` is attached only by the FastAPI adapter and is never
  returned to the browser or written to logs
- Planned datasets: passenger volume and traffic speed bands where licence and
  retention conditions permit

## NEA PSI and PM2.5 readings

- Provider: data.gov.sg / National Environment Agency
- Endpoints: `/v2/real-time/api/psi` and `/v2/real-time/api/pm25`
- Authentication: none
- Current use: five-region 24-hour PSI, 24-hour PM2.5, and one-hour PM2.5
- Quality checks: five expected regions, coordinates, all three readings,
  observation and update timestamps, API status codes
- Presentation: the highest regional 24-hour PSI drives the national alert band;
  each regional value remains visible so the user can make a local decision

## Historical NEA PSI archive

- Provider: data.gov.sg / National Environment Agency
- Collection: Historical Pollutant Standards Index, collection `2215`
- Current training datasets: 2023 and 2024 hourly regional CSVs
- Current use: one-hour-ahead regional 24-hour PSI forecasting and backtesting
- Retrieval: official dataset initiate-download and poll-download APIs
- Reproducibility: raw files remain local; SHA-256 checksums, dataset IDs, time
  partitions, and model package versions are recorded for every experiment
- Source caveat: data.gov.sg states that the archive can contain missing records
  and has not undergone the quality control used for official climate records

PSI bands follow Singapore's official categories: Good (0-50), Moderate
(51-100), Unhealthy (101-200), Very Unhealthy (201-300), and Hazardous
(above 300). Citizen guidance links to `haze.gov.sg`; FluxSG does not replace
official health, school, workplace, or medical advice.

Before persisting any additional LTA dataset, its current licence, rate limits,
retention conditions, and attribution requirements will be recorded here.

## Data governance

- No personal data is needed or intentionally collected.
- Every stored record will include source and ingestion timestamps.
- Rejected records will be quarantined with a machine-readable reason.
- Raw, cleaned, and analytical datasets will have separate schemas and access
  policies.
