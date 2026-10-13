from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.pipelines.snapshot import (
    SnapshotIngestion,
    extract_rejections,
    fingerprint,
    record_counts,
)
from app.pipelines.worker import with_retries


class FakeLedger:
    def __init__(self) -> None:
        self.keys: dict[str, UUID] = {}
        self.completed: list[tuple[UUID, str, int, int, int, str | None]] = []
        self.failed: list[tuple[UUID, str]] = []
        self.refreshed: list[tuple[str, str, str | None]] = []

    async def begin(self, dataset: str, idempotency_key: str) -> UUID | None:
        if idempotency_key in self.keys:
            return None
        run_id = uuid4()
        self.keys[idempotency_key] = run_id
        return run_id

    async def complete(
        self,
        run_id: UUID,
        object_key: str,
        received: int,
        valid: int,
        rejected: int,
        quarantine_key: str | None,
    ) -> None:
        self.completed.append((run_id, object_key, received, valid, rejected, quarantine_key))

    async def fail(self, run_id: UUID, message: str) -> None:
        self.failed.append((run_id, message))

    async def refresh_storage_keys(
        self,
        idempotency_key: str,
        object_key: str,
        quarantine_key: str | None,
    ) -> None:
        self.refreshed.append((idempotency_key, object_key, quarantine_key))


class FakeStore:
    def __init__(self) -> None:
        self.calls = 0
        self.objects: dict[str, dict[str, Any]] = {}
        self.quarantine: dict[str, list[dict[str, Any]]] = {}

    def put_json(self, dataset: str, digest: str, payload: dict[str, Any]) -> str:
        self.calls += 1
        key = f"{dataset}/{digest}.json"
        self.objects.setdefault(key, payload)
        return key

    def put_quarantine(
        self,
        dataset: str,
        digest: str,
        records: list[dict[str, Any]],
    ) -> str:
        key = f"quarantine/{dataset}/{digest}.json"
        self.quarantine.setdefault(key, records)
        return key


@pytest.mark.asyncio
async def test_snapshot_ingestion_is_idempotent_and_records_quality() -> None:
    ledger = FakeLedger()
    store = FakeStore()
    ingestion = SnapshotIngestion(ledger, store)
    payload = {
        "ingested_at": datetime.now(UTC).isoformat(),
        "records": [{"id": 1}],
        "quality": {"received_records": 2, "valid_records": 1},
    }

    first = await ingestion.ingest("example", payload)
    second = await ingestion.ingest(
        "example",
        {**payload, "ingested_at": "2099-01-01T00:00:00+00:00"},
    )

    assert first.status == "completed"
    assert second.status == "duplicate"
    assert store.calls == 2
    assert len(store.objects) == 1
    assert ledger.completed[0][2:] == (2, 1, 1, None)
    assert ledger.refreshed == [(second.idempotency_key, second.object_key, None)]


@pytest.mark.asyncio
async def test_rejected_records_are_written_to_quarantine() -> None:
    ledger = FakeLedger()
    store = FakeStore()
    ingestion = SnapshotIngestion(ledger, store)
    payload = {
        "datasets": {
            "bus_stops": {
                "records": [{"BusStopCode": "01012"}],
                "rejected_records": [{"BusStopCode": None}],
            }
        },
        "quality": {
            "received_records": 2,
            "valid_records": 1,
            "rejected_records": 1,
        },
    }

    outcome = await ingestion.ingest("lta_transport_network", payload)

    assert outcome.quarantine_key is not None
    assert outcome.quarantine_key in store.quarantine
    assert store.quarantine[outcome.quarantine_key] == [
        {"source": "bus_stops", "record": {"BusStopCode": None}}
    ]
    assert ledger.completed[0][-1] == outcome.quarantine_key


def test_extract_rejections_supports_root_and_nested_contracts() -> None:
    payload = {
        "rejected_records": [{"reason": "root"}],
        "datasets": {
            "routes": {"rejected_records": [{"reason": "nested"}]},
            "services": {"records": []},
        },
    }

    assert extract_rejections(payload) == [
        {"source": "root", "record": {"reason": "root"}},
        {"source": "routes", "record": {"reason": "nested"}},
    ]


def test_fingerprint_ignores_only_pipeline_timestamps() -> None:
    original = {"ingested_at": "one", "observed_at": "source-one", "value": 10}
    same_source = {"ingested_at": "two", "observed_at": "source-one", "value": 10}
    new_source = {"ingested_at": "two", "observed_at": "source-two", "value": 10}

    assert fingerprint(original) == fingerprint(same_source)
    assert fingerprint(original) != fingerprint(new_source)
    assert record_counts({"quality": {"received_records": 3, "valid_records": 2}}) == (
        3,
        2,
        1,
    )


@pytest.mark.asyncio
async def test_retry_limit_recovers_from_a_transient_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary")
        return "ok"

    async def no_wait(_: float) -> None:
        return None

    monkeypatch.setattr("app.pipelines.worker.asyncio.sleep", no_wait)

    assert await with_retries(operation, max_attempts=3) == "ok"
    assert attempts == 2
