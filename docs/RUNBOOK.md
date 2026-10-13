# Ingestion recovery runbook

## 1. Establish impact

```bash
docker compose ps
curl -fsS http://localhost:8000/health
curl -fsS 'http://localhost:8000/api/v1/pipeline/status?limit=20'
curl -fsS http://localhost:9090/api/v1/targets
docker compose logs --since=30m worker
```

Use the structured log `trace_id` in Jaeger at `http://localhost:16686` to
separate an upstream timeout, contract rejection, database failure, or object
store failure.

## 2. Recover safely

- Upstream timeout: confirm the official source is reachable, then run one
  bounded cycle with `docker compose run --rm worker python -m app.pipelines.worker --once`.
- Database unavailable: restore PostgreSQL first. The worker's schema bootstrap
  safely adds missing columns, and failed ledger entries can be retried.
- Object missing: rerun one cycle. Deterministic keys restore the object without
  duplicating the ledger record.
- Rejected records: inspect the ledger's `quarantine_key`; fix the adapter or
  upstream contract before promoting any quarantined row.
- Trace or metric missing: check the Jaeger and Prometheus containers, then
  verify `OTEL_EXPORTER_OTLP_ENDPOINT` and the two Prometheus scrape targets.

Never edit a raw or quarantine object in place. Correct the contract and replay
the source into a new content-addressed object.

## 3. Confirm recovery

```bash
docker compose run --rm worker python -m app.pipelines.worker --once
curl -fsS 'http://localhost:8000/api/v1/pipeline/status?limit=5'
curl -fsS http://localhost:9100/metrics | grep fluxsg_ingestion_runs_total
```

Recovery is complete when the affected dataset has a completed or duplicate
run, Prometheus reports both targets up, and Jaeger shows a non-error worker
span. Record any quarantined object key before closing the incident.
