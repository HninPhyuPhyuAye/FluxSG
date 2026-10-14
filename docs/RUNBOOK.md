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

## API SLO alert

1. Check the outside-in `Production smoke checks` workflow.
2. Separate 5xx errors from upstream latency in the Grafana request panels.
3. Inspect the matching route in `/metrics`, then follow its trace in Jaeger.
4. If the failure is upstream, keep the last successful forecast manifest and
   allow its expiry guard to withhold stale values.
5. Confirm availability and p95 return within objective before resolving.

## Ingestion freshness alert

1. Compare `time() - fluxsg_ingestion_last_success_unixtime` by dataset.
2. Inspect the worker log and trace for the affected dataset.
3. Run one bounded recovery cycle; never run overlapping unbounded retries.
4. Confirm a completed or duplicate ledger record and a reset freshness gauge.

## Backup and restore drill

Run `make backup` followed by `make restore-drill`. The drill verifies checksums,
restores PostgreSQL into the isolated `fluxsg_restore_drill` database, checks
that application tables exist, and removes the drill database. It never
overwrites the normal `fluxsg` database.
