# Observability

FluxSG's local platform exposes the three signals needed to diagnose ingestion:
structured JSON logs, Prometheus metrics, and OpenTelemetry traces.

## Start and inspect

```bash
docker compose up --build -d
docker compose logs -f worker
open http://localhost:9090
open http://localhost:16686
```

| Signal | Local endpoint | What to inspect |
| --- | --- | --- |
| API metrics | `http://localhost:8000/metrics` | Request count and latency |
| Worker metrics | `http://localhost:9100/metrics` | Runs, records, latency, last success |
| Prometheus | `http://localhost:9090/targets` | Both FluxSG targets must be `UP` |
| Jaeger | `http://localhost:16686` | `fluxsg-api` and `fluxsg-worker` traces |

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
