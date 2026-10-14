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

- [x] Time-based train/validation/test split
- [x] Naive seasonal and persistence baselines
- [x] Candidate forecasting model and leakage-safe feature pipeline
- [x] Expanding-window backtesting, uncertainty intervals, and drift monitoring
- [x] Model card covering limits and failure modes

**Evidence:** honest model comparison and reproducible experiment tracking.

## Milestone 5 - Production delivery

- [x] Terraform-managed cloud environment
- [x] Hourly freshness- and drift-gated forecast publication
- [x] FastAPI forecast contract and citizen-facing release decision
- [x] Automated build, CodeQL/dependency scanning, and deployment
- [x] Dashboards, SLOs, alerting, backup, and restore drill
- [x] Load test and cost report

**Evidence:** live system, operational runbook, performance and cost results.

## Milestone 6 - Air-aware citizen experience

- [x] Join live LTA arrivals with the nearest official regional air reading
- [x] Publish an explainable, bounded commute exposure signal
- [x] Add a five-region Singapore air-quality schematic
- [x] Save a regional PSI watch and threshold locally on the citizen's device
- [x] Offer user-initiated browser alerts while the dashboard is open
- [x] Add an installable, offline-shell PWA manifest and service worker
- [x] Extend API, browser, and outside-in production checks
- [x] Document score components, limitations, and privacy boundaries

**Evidence:** one-request cross-domain decision contract, live citizen workflow,
transparent scoring, local-only preference storage, and deployment verification.
