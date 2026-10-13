# Roadmap

## Milestone 1 - Trusted live vertical slice

- [x] Monorepo foundation and project documentation
- [x] Live data.gov.sg weather adapter
- [x] Five-region PSI and PM2.5 haze watch with official guidance link
- [x] Normalised API contract and data-quality summary
- [x] Responsive operations dashboard
- [x] API unit tests and CI workflow
- [x] Public preview deployment

**Evidence:** working demo, source-health states, tests, architecture record.

## Milestone 2 - Reproducible ingestion

- [x] Authenticated LTA DataMall client with bounded pagination and caching
- [x] Normalised bus-stop, service, route, and live-arrival contracts
- [x] Citizen stop search with crowding and accessibility indicators
- [x] LTA adapter unit tests and live Docker verification
- [x] PostgreSQL and object-storage development services
- [x] Scheduled ingestion with idempotency and retry limits
- [x] Immutable raw records and rejected-record quarantine
- [x] OpenTelemetry traces, structured logs, and pipeline metrics

**Evidence:** replayable pipeline, failure injection, recovery runbook.

## Milestone 3 - Analytics warehouse

- [x] Bronze, silver, and gold data contracts
- [x] dbt staging, dimensional models, documentation, and lineage
- [x] Freshness, uniqueness, relationship, and domain tests
- [x] Analyst-ready views and three documented business questions

**Evidence:** lineage graph, quality report, reproducible SQL analysis.

## Milestone 4 - Forecasting

- Time-based train/validation/test split
- Naive seasonal baseline
- Candidate forecasting model and feature pipeline
- Backtesting, uncertainty intervals, and drift monitoring
- Model card covering limits and failure modes

**Evidence:** honest model comparison and reproducible experiment tracking.

## Milestone 5 - Production delivery

- Terraform-managed cloud environment
- Automated build, security scanning, and deployment
- Dashboards, SLOs, alerting, backup, and restore drill
- Load test and cost report

**Evidence:** live system, operational runbook, performance and cost results.

