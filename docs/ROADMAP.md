# Roadmap

## Milestone 1 - Trusted live vertical slice

- [x] Monorepo foundation and project documentation
- [x] Live data.gov.sg weather adapter
- [x] Normalised API contract and data-quality summary
- [x] Responsive operations dashboard
- [x] API unit tests and CI workflow
- [ ] Public preview deployment

**Evidence:** working demo, source-health states, tests, architecture record.

## Milestone 2 - Reproducible ingestion

- PostgreSQL and object-storage development services
- Scheduled ingestion with idempotency and retry limits
- Immutable raw records and rejected-record quarantine
- OpenTelemetry traces, structured logs, and pipeline metrics
- LTA bus-stop and route adapters after account-key configuration

**Evidence:** replayable pipeline, failure injection, recovery runbook.

## Milestone 3 - Analytics warehouse

- Bronze, silver, and gold data contracts
- dbt staging, dimensional models, documentation, and lineage
- Freshness, uniqueness, relationship, and domain tests
- Analyst-ready views and three documented business questions

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

