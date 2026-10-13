import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from app.clients.air_quality import AirQualityClient
from app.clients.lta import LtaDataMallClient
from app.clients.weather import WeatherClient
from app.core.config import Settings, get_settings
from app.pipelines.snapshot import (
    PostgresIngestionLedger,
    S3SnapshotStore,
    SnapshotIngestion,
)


def log(event: str, **details: Any) -> None:
    print(
        json.dumps(
            {"timestamp": datetime.now(UTC).isoformat(), "event": event, **details},
            sort_keys=True,
            default=str,
        ),
        flush=True,
    )


async def with_retries[T](
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int,
) -> T:
    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception:
            if attempt == max_attempts:
                raise
            await asyncio.sleep(2 ** (attempt - 1))
    raise RuntimeError("retry loop exited unexpectedly")


def require_pipeline_settings(settings: Settings) -> tuple[str, str, str, str]:
    required = {
        "DATABASE_URL": settings.database_url,
        "OBJECT_STORE_ENDPOINT": settings.object_store_endpoint,
        "OBJECT_STORE_ACCESS_KEY": settings.object_store_access_key,
        "OBJECT_STORE_SECRET_KEY": settings.object_store_secret_key,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing pipeline settings: {', '.join(missing)}")
    return (
        settings.database_url or "",
        settings.object_store_endpoint or "",
        settings.object_store_access_key or "",
        settings.object_store_secret_key or "",
    )


async def run_cycle(settings: Settings, ingestion: SnapshotIngestion) -> None:
    weather = WeatherClient(settings.data_gov_weather_url, settings.source_timeout_seconds)
    air_quality = AirQualityClient(
        settings.data_gov_psi_url,
        settings.data_gov_pm25_url,
        settings.source_timeout_seconds,
    )
    jobs: list[tuple[str, Callable[[], Awaitable[Any]]]] = [
        ("weather_outlook", weather.fetch),
        ("air_quality", air_quality.fetch),
    ]
    if settings.lta_account_key:
        lta = LtaDataMallClient(
            settings.lta_account_key,
            settings.lta_base_url,
            settings.source_timeout_seconds,
            settings.lta_cache_ttl_seconds,
        )
        jobs.append(("lta_transport_network", lta.fetch_network_snapshot))

    for dataset, fetch in jobs:
        try:
            value = await with_retries(fetch, max_attempts=settings.ingestion_max_attempts)
            outcome = await ingestion.ingest(dataset, value)
            log(
                "ingestion_finished",
                dataset=dataset,
                status=outcome.status,
                object_key=outcome.object_key,
            )
        except Exception as exc:
            log("ingestion_failed", dataset=dataset, error=str(exc))


async def main(once: bool = False) -> None:
    settings = get_settings()
    database_url, endpoint, access_key, secret_key = require_pipeline_settings(settings)
    ledger = PostgresIngestionLedger(database_url)
    store = S3SnapshotStore(
        endpoint,
        access_key,
        secret_key,
        settings.object_store_bucket,
        settings.object_store_secure,
    )
    await with_retries(ledger.initialise, max_attempts=10)
    await with_retries(
        lambda: asyncio.to_thread(store.initialise),
        max_attempts=10,
    )
    ingestion = SnapshotIngestion(ledger, store)

    while True:
        await run_cycle(settings, ingestion)
        if once:
            return
        await asyncio.sleep(settings.ingestion_interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FluxSG snapshot ingestion")
    parser.add_argument("--once", action="store_true", help="Run one ingestion cycle")
    arguments = parser.parse_args()
    asyncio.run(main(once=arguments.once))
