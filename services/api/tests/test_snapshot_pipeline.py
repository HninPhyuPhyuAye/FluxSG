from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.pipelines.snapshot import SnapshotIngestion, fingerprint, record_counts
from app.pipelines.worker import with_retries


class FakeLedger:
    def __init__(self) -> None:
        self.keys: dict[str, UUID] = {}
        self.completed: list[tuple[UUID, str, int, int, int]] = []
        self.failed: list[tuple[UUID, str]] = []

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
    ) -> None:
        self.completed.append((run_id, object_key, received, valid, rejected))

    async def fail(self, run_id: UUID, message: str) -> None:
        self.failed.append((run_id, message))


class FakeStore:
    def __init__(self) -> None:
        self.calls = 0
        self.objects: dict[str, dict[str, Any]] = {}

    def put_json(self, dataset: str, digest: str, payload: dict[str, Any]) -> str:
        self.calls += 1
        key = f"{dataset}/{digest}.json"
        self.objects.setdefault(key, payload)
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
    assert ledger.completed[0][2:] == (2, 1, 1)


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
