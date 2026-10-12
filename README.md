# FluxSG

**Singapore movement intelligence, engineered in the open.**

FluxSG is a portfolio-grade data platform for understanding how weather and
transport conditions affect movement across Singapore. It is being built as a
real production system rather than a dashboard-only demo: source adapters,
quality contracts, historical storage, transformations, forecasting,
observable APIs, and an accessible decision interface.

## Current milestone

Milestone 1 establishes a tested vertical slice:

- a FastAPI service that normalises the live NEA two-hour forecast;
- a citizen-facing haze watch combining official PSI and PM2.5 feeds;
- explicit freshness, completeness, and source-health signals;
- an LTA DataMall readiness endpoint without exposing credentials;
- a responsive Next.js operations dashboard;
- containerised local development and automated CI checks.

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
disabled until that variable is present.

## Quality commands

```bash
make check
```

## Delivery roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the milestone plan and recruiter
evidence produced by each phase.

## Responsible use

FluxSG is an independent portfolio project. It is not affiliated with or
endorsed by Singapore's Land Transport Authority, NEA, or data.gov.sg. Source
availability and timestamps are always shown; predictions will be labelled as
estimates and never presented as official operational guidance.

