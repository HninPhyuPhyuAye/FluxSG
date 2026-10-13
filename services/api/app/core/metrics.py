from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "fluxsg_http_requests_total",
    "HTTP requests handled by the FluxSG API.",
    ("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "fluxsg_http_request_duration_seconds",
    "Time spent handling FluxSG API requests.",
    ("method", "route"),
)
INGESTION_RUNS = Counter(
    "fluxsg_ingestion_runs_total",
    "Ingestion runs by dataset and result.",
    ("dataset", "status"),
)
INGESTION_RECORDS = Counter(
    "fluxsg_ingestion_records_total",
    "Ingestion records by dataset and validation result.",
    ("dataset", "result"),
)
INGESTION_DURATION = Histogram(
    "fluxsg_ingestion_duration_seconds",
    "End-to-end fetch, validation, and storage time for an ingestion dataset.",
    ("dataset",),
)
INGESTION_LAST_SUCCESS = Gauge(
    "fluxsg_ingestion_last_success_unixtime",
    "Unix timestamp of the last successful ingestion run.",
    ("dataset",),
)


def record_ingestion(
    dataset: str,
    status: str,
    duration_seconds: float,
    received: int = 0,
    valid: int = 0,
    rejected: int = 0,
) -> None:
    INGESTION_RUNS.labels(dataset, status).inc()
    INGESTION_DURATION.labels(dataset).observe(duration_seconds)
    if status in {"completed", "duplicate"}:
        INGESTION_RECORDS.labels(dataset, "received").inc(received)
        INGESTION_RECORDS.labels(dataset, "valid").inc(valid)
        INGESTION_RECORDS.labels(dataset, "rejected").inc(rejected)
        INGESTION_LAST_SUCCESS.labels(dataset).set_to_current_time()
