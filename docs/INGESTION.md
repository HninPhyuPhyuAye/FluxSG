# Reproducible ingestion

FluxSG now runs a local scheduled ingestion plane alongside the live API. The
worker fetches official weather, air-quality, and LTA network data, validates it
through the same source contracts used by the API, and writes immutable JSON
snapshots to S3-compatible object storage.

## Runtime flow

```text
data.gov.sg + LTA DataMall
            |
     bounded fetch + validation
            |
    content fingerprint (SHA-256)
       /                 \
SeaweedFS object store   PostgreSQL ingestion ledger
immutable JSON objects   run state + quality counts + object keys
            |
 rejected rows -> isolated quarantine prefix
```

The fingerprint excludes FluxSG's own ingestion timestamp but retains source
timestamps. Re-fetching an unchanged source therefore produces the same
idempotency key and object name. Failed runs can be retried, while completed
runs are not duplicated.

## Local services

```bash
docker compose up --build -d
docker compose logs -f worker
curl http://localhost:8000/api/v1/pipeline/status
```

| Service | Local endpoint | Purpose |
| --- | --- | --- |
| FastAPI | `http://localhost:8000` | Live and pipeline-status APIs |
| PostgreSQL | `127.0.0.1:5432` | Ingestion ledger |
| SeaweedFS S3 | `127.0.0.1:8333` | Immutable source snapshots |
| Worker | internal | Scheduled, bounded ingestion |
| Worker metrics | `http://127.0.0.1:9100/metrics` | Pipeline counters and latency |

Run a single cycle without waiting for the schedule:

```bash
docker compose run --rm worker python -m app.pipelines.worker --once
```

The local object-store credentials in `.env.example` are development-only.
The S3 port is bound to loopback, anonymous access is disabled, and the real
LTA AccountKey is never written to stored objects, logs, or the ledger.

## Rejected-record quarantine

The complete validated source response remains in its immutable raw object. If
an adapter also reports malformed rows, FluxSG copies only those rows—with the
source dataset name and rejection reason—into a separate deterministic path:

```text
raw/<dataset>/sha256=<first-two-characters>/<sha256>.json
quarantine/<dataset>/sha256=<first-two-characters>/<sha256>.json
```

These paths depend only on dataset and content, so the same payload keeps the
same object name even when it is replayed on a different day.

The PostgreSQL run links `object_key` and `quarantine_key`, making every
rejection traceable without mixing bad rows into downstream analytics.

Run the deterministic failure injection twice to prove both quarantine and
idempotency. The first run returns `completed`; the second returns `duplicate`,
and only one raw object, one quarantine object, and one ledger row remain.

```bash
docker compose run --rm worker python -m app.pipelines.failure_injection
docker compose run --rm worker python -m app.pipelines.failure_injection
curl 'http://localhost:8000/api/v1/pipeline/status?limit=5'
```

## Failure behaviour

- Each source fetch has a finite retry limit with exponential backoff.
- A unique PostgreSQL idempotency key prevents duplicate completed runs.
- Deterministic object names make repeat writes safe and allow missing objects
  to be restored from the official source.
- Every run records received, valid, and rejected counts for later monitoring.
- Source failures are logged as structured JSON and do not stop other datasets.
- Completed logs include `trace_id`, `span_id`, duration, object, and quarantine keys.

Recovery procedures are in [`RUNBOOK.md`](RUNBOOK.md). Metrics and traces are
documented in [`OBSERVABILITY.md`](OBSERVABILITY.md).
