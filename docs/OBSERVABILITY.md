# Observability

FluxSG's local platform exposes the three signals needed to diagnose ingestion:
structured JSON logs, Prometheus metrics, OpenTelemetry traces, and a
provisioned Grafana SLO dashboard.

## Start and inspect

```bash
docker compose up --build -d
docker compose logs -f worker
open http://localhost:9090
open http://localhost:16686
open http://localhost:3001
```

| Signal | Local endpoint | What to inspect |
| --- | --- | --- |
| API metrics | `http://localhost:8000/metrics` | Request count and latency |
| Worker metrics | `http://localhost:9100/metrics` | Runs, records, latency, last success |
| Prometheus | `http://localhost:9090/targets` | Both FluxSG targets must be `UP` |
| Jaeger | `http://localhost:16686` | `fluxsg-api` and `fluxsg-worker` traces |
| Grafana | `http://localhost:3001` | Availability, latency, freshness, and ingestion outcomes |

## Service objectives

| SLO | Objective | Alert |
|---|---:|---|
| API availability | 99.5% over 30 days | 15 minutes below objective |
| API p95 latency | under 750 ms over 15 minutes | 15 minutes above objective |
| ingestion freshness | under 30 minutes | 10 minutes above objective |

Recording and alert rules live in `infra/prometheus/rules/fluxsg-slos.yml`.
The twice-hourly GitHub smoke check provides an independent outside-in signal
for the public API, forecast contract, and dashboard.

The local Compose stack sends OTLP/HTTP spans directly to Jaeger. Jaeger uses
in-memory storage here, so local traces disappear when its container is
recreated. Production can set `OTEL_EXPORTER_OTLP_ENDPOINT` to any compatible
collector without changing application code.

## Pipeline metrics

```text
fluxsg_ingestion_runs_total{dataset,status}
fluxsg_ingestion_records_total{dataset,result}
fluxsg_ingestion_duration_seconds{dataset}
fluxsg_ingestion_last_success_unixtime{dataset}
```

Useful PromQL checks:

```promql
sum by (dataset, status) (increase(fluxsg_ingestion_runs_total[1h]))
sum by (dataset) (increase(fluxsg_ingestion_records_total{result="rejected"}[1h]))
histogram_quantile(0.95, sum by (le, dataset) (rate(fluxsg_ingestion_duration_seconds_bucket[15m])))
time() - fluxsg_ingestion_last_success_unixtime
```

Worker log events are one-line JSON. Every ingestion completion or failure
contains the dataset, duration, and active OpenTelemetry `trace_id` and
`span_id`, so a log can be followed directly into the corresponding trace.
