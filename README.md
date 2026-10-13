# FluxSG

**Singapore movement intelligence, engineered in the open.**

FluxSG is a portfolio-grade data platform for understanding how weather and
transport conditions affect movement across Singapore. It is being built as a
real production system rather than a dashboard-only demo: source adapters,
quality contracts, historical storage, transformations, forecasting,
observable APIs, and an accessible decision interface.

## Live dashboard

**[Open FluxSG](https://hninphyuphyuaye.github.io/FluxSG/)**

The public dashboard combines official data.gov.sg environmental readings with
live LTA DataMall transport intelligence. Its secured FastAPI backend is
deployed at **[fluxsg-api.vercel.app](https://fluxsg-api.vercel.app/docs)**;
the LTA AccountKey remains server-side and is never included in the browser
bundle.

## Current milestone

Milestone 2 extends the tested vertical slice with a secured LTA transport layer:

- a FastAPI service that normalises the live NEA two-hour forecast;
- a citizen-facing haze watch combining official PSI and PM2.5 feeds;
- an authenticated LTA adapter covering all bus stops and active services;
- searchable stop metadata and live next-three-bus arrival boards;
- route lookup with scheduled first and last bus timings;
- scheduled, idempotent source snapshots in S3-compatible object storage;
- a PostgreSQL ingestion ledger with quality counts and object provenance;
- explicit freshness, completeness, and source-health signals;
- a responsive Next.js operations dashboard;
- containerised local development and automated CI checks.
- public delivery through GitHub Pages.

## Architecture

```text
data.gov.sg / LTA DataMall
           |
     source adapters
           |
  validation + contracts
           |
      FastAPI service
           |
  Next.js decision dashboard
```

The planned warehouse and forecasting layers are documented in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Run locally

### With Docker

```bash
cp .env.example .env
docker compose up --build
```

Open <http://localhost:3000>. API documentation is available at
<http://localhost:8000/docs>.

The ingestion ledger is available at
<http://localhost:8000/api/v1/pipeline/status>. PostgreSQL and the local
S3-compatible object store are started automatically with the API, worker, and
web dashboard.

The secured local build activates the transport search. Try `01012` or
`Raffles`, select a stop, and FluxSG will request the current LTA arrival board.

### Without Docker

```bash
pnpm install
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e 'services/api[dev]'
make api
```

In a second terminal:

```bash
pnpm dev
```

## Configuration

Copy `.env.example` to `.env`. The weather vertical slice works without a
credential. LTA DataMall integration requires a free `LTA_ACCOUNT_KEY` and is
disabled until that variable is present. The key is consumed only by FastAPI;
it is never included in the Next.js client bundle or API responses.

## Transport API

```text
GET /api/v1/transport/network
GET /api/v1/transport/stops?query=Raffles&limit=8
GET /api/v1/transport/arrivals/01012
GET /api/v1/transport/routes/10
```

Static network datasets are cached for six hours to avoid wasteful upstream
requests. Live arrivals are fetched on demand from LTA DataMall.

## Quality commands

```bash
make check
```

## Delivery roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the milestone plan and recruiter
evidence produced by each phase.

Deployment architecture and secret-handling instructions are documented in
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

The snapshot lifecycle, idempotency contract, and local inspection commands are
documented in [`docs/INGESTION.md`](docs/INGESTION.md).

## Responsible use

FluxSG is an independent portfolio project. It is not affiliated with or
endorsed by Singapore's Land Transport Authority, NEA, or data.gov.sg. Source
availability and timestamps are always shown; predictions will be labelled as
estimates and never presented as official operational guidance.

