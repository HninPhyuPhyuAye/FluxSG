# Architecture

## Target design

```mermaid
flowchart LR
  LTA[LTA DataMall] --> I[Python ingestion]
  NEA[data.gov.sg weather] --> I
  I --> R[(Raw object storage)]
  R --> B[(Bronze JSONB)]
  I --> Q[Rejected-record quarantine]
  Q --> B
  B --> S[dbt silver views]
  S --> G[dbt gold marts]
  G --> F[Forecast training]
  G --> A[FastAPI]
  F --> A
  A --> UI[Next.js dashboard]
  I --> O[Metrics + logs]
  A --> O
```

## Design decisions

- **Adapters isolate providers.** External payload changes should not leak into
  domain models or UI code.
- **Raw data is immutable.** Reprocessing and incident investigation require
  the original source payload and ingestion timestamp.
- **Quality is a first-class output.** Freshness, completeness, uniqueness, and
  validity are visible to users and monitored like application health.
- **Forecasting starts with a baseline.** A complex model is shipped only if it
  beats a transparent naive prediction on held-out time periods.
- **Credentials stay server-side.** LTA keys are read from environment or a
  cloud secret manager and never sent to the browser.
- **Static transport metadata is bounded and cached.** The LTA adapter follows
  the provider's 500-record pagination contract, applies hard page limits, and
  caches bus stops, services, and routes for six hours. Arrival boards remain
  on-demand because their source refreshes every 20 seconds.
- **The public dashboard uses a secured API with a resilient fallback.** GitHub
  Pages calls the Vercel-hosted FastAPI service for authenticated LTA traffic
  and validated environmental data. The AccountKey remains server-side. If the
  API is unavailable, the static dashboard falls back to CORS-enabled,
  unauthenticated data.gov.sg feeds rather than exposing a credential.

## Repository layout

```text
apps/web/          Next.js decision dashboard
services/api/      FastAPI source and domain API
services/api/app/pipelines/ scheduled snapshot ingestion and run ledger
infra/             local PostgreSQL and S3-compatible storage configuration
warehouse/         bronze loader, dbt models, tests, analyses, and fixtures
docs/              product, data, architecture, and delivery evidence
.github/workflows/ automated quality gates
```

The warehouse implements the medallion design end to end. Immutable source
objects become queryable bronze JSONB records, silver views normalise provider
payloads, and contracted gold models expose dimensional and analytical data.
See [`WAREHOUSE.md`](WAREHOUSE.md) for lineage and reproducible evidence.

