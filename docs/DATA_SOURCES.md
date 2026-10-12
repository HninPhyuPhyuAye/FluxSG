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

Before persisting any LTA dataset, its current licence, rate limits, retention
conditions, and attribution requirements will be recorded here.

## Data governance

- No personal data is needed or intentionally collected.
- Every stored record will include source and ingestion timestamps.
- Rejected records will be quarantined with a machine-readable reason.
- Raw, cleaned, and analytical datasets will have separate schemas and access
  policies.

