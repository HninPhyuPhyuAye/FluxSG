import asyncio
import json
from datetime import UTC, datetime

from app.core.config import get_settings
from app.pipelines.snapshot import PostgresIngestionLedger, S3SnapshotStore, SnapshotIngestion
from app.pipelines.worker import require_pipeline_settings


async def main() -> None:
    """Inject one deterministic rejected record to prove quarantine and replay behaviour."""
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
    await ledger.initialise()
    await asyncio.to_thread(store.initialise)
    outcome = await SnapshotIngestion(ledger, store).ingest(
        "pipeline_contract_test",
        {
            "contract_version": 1,
            "ingested_at": datetime.now(UTC).isoformat(),
            "records": [{"stop_code": "01012", "status": "valid"}],
            "rejected_records": [
                {
                    "raw": {"BusStopCode": None, "Description": "controlled failure"},
                    "reason": "BusStopCode is required",
                }
            ],
            "quality": {
                "received_records": 2,
                "valid_records": 1,
                "rejected_records": 1,
            },
        },
    )
    print(json.dumps(outcome.__dict__, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
