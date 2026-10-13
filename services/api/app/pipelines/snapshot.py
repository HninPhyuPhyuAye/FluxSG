import asyncio
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlparse
from uuid import UUID, uuid4

import asyncpg
from minio import Minio
from minio.error import S3Error
from pydantic import BaseModel

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id UUID PRIMARY KEY,
    dataset TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    received_records INTEGER NOT NULL DEFAULT 0,
    valid_records INTEGER NOT NULL DEFAULT 0,
    rejected_records INTEGER NOT NULL DEFAULT 0,
    object_key TEXT,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS ingestion_runs_dataset_started_idx
    ON ingestion_runs (dataset, started_at DESC);
"""


@dataclass(frozen=True)
class IngestionOutcome:
    dataset: str
    status: str
    idempotency_key: str
    object_key: str | None = None


class Ledger(Protocol):
    async def begin(self, dataset: str, idempotency_key: str) -> UUID | None: ...

    async def complete(
        self,
        run_id: UUID,
        object_key: str,
        received: int,
        valid: int,
        rejected: int,
    ) -> None: ...

    async def fail(self, run_id: UUID, message: str) -> None: ...


class SnapshotStore(Protocol):
    def put_json(self, dataset: str, fingerprint: str, payload: dict[str, Any]) -> str: ...


class PostgresIngestionLedger:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    async def initialise(self) -> None:
        connection = await asyncpg.connect(self.database_url)
        try:
            await connection.execute(SCHEMA_SQL)
        finally:
            await connection.close()

    async def begin(self, dataset: str, idempotency_key: str) -> UUID | None:
        run_id = uuid4()
        connection = await asyncpg.connect(self.database_url)
        try:
            row = await connection.fetchrow(
                """
                INSERT INTO ingestion_runs (
                    run_id, dataset, idempotency_key, status, started_at
                ) VALUES ($1, $2, $3, 'running', NOW())
                ON CONFLICT (idempotency_key) DO UPDATE
                SET status = 'running', started_at = NOW(), completed_at = NULL,
                    error_message = NULL
                WHERE ingestion_runs.status = 'failed'
                RETURNING run_id
                """,
                run_id,
                dataset,
                idempotency_key,
            )
            return row["run_id"] if row else None
        finally:
            await connection.close()

    async def complete(
        self,
        run_id: UUID,
        object_key: str,
        received: int,
        valid: int,
        rejected: int,
    ) -> None:
        connection = await asyncpg.connect(self.database_url)
        try:
            await connection.execute(
                """
                UPDATE ingestion_runs
                SET status = 'completed', completed_at = NOW(), object_key = $2,
                    received_records = $3, valid_records = $4, rejected_records = $5
                WHERE run_id = $1
                """,
                run_id,
                object_key,
                received,
                valid,
                rejected,
            )
        finally:
            await connection.close()

    async def fail(self, run_id: UUID, message: str) -> None:
        connection = await asyncpg.connect(self.database_url)
        try:
            await connection.execute(
                """
                UPDATE ingestion_runs
                SET status = 'failed', completed_at = NOW(), error_message = $2
                WHERE run_id = $1
                """,
                run_id,
                message[:500],
            )
        finally:
            await connection.close()

    async def latest(self, limit: int = 20) -> list[dict[str, Any]]:
        connection = await asyncpg.connect(self.database_url)
        try:
            rows = await connection.fetch(
                """
                SELECT run_id, dataset, status, started_at, completed_at,
                       received_records, valid_records, rejected_records, object_key
                FROM ingestion_runs
                ORDER BY started_at DESC
                LIMIT $1
                """,
                limit,
            )
            return [dict(row) for row in rows]
        finally:
            await connection.close()


class S3SnapshotStore:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
        self.bucket = bucket
        self.client = Minio(
            parsed.netloc or parsed.path,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure or parsed.scheme == "https",
        )

    def initialise(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def put_json(self, dataset: str, fingerprint: str, payload: dict[str, Any]) -> str:
        ingested_at = datetime.now(UTC)
        object_key = (
            f"{dataset}/year={ingested_at:%Y}/month={ingested_at:%m}/"
            f"day={ingested_at:%d}/{fingerprint}.json"
        )
        try:
            self.client.stat_object(self.bucket, object_key)
            return object_key
        except S3Error as exc:
            if exc.code not in {"NoSuchKey", "NoSuchObject"}:
                raise

        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        self.client.put_object(
            self.bucket,
            object_key,
            io.BytesIO(body),
            len(body),
            content_type="application/json",
        )
        return object_key


def json_payload(value: BaseModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return json.loads(json.dumps(value, default=str))


def _without_volatile_timestamps(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_volatile_timestamps(item)
            for key, item in value.items()
            if key not in {"ingested_at", "fetched_at"}
        }
    if isinstance(value, list):
        return [_without_volatile_timestamps(item) for item in value]
    return value


def fingerprint(payload: dict[str, Any]) -> str:
    stable = _without_volatile_timestamps(payload)
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def record_counts(payload: dict[str, Any]) -> tuple[int, int, int]:
    quality = payload.get("quality", {})
    if not isinstance(quality, dict):
        return 0, 0, 0
    received = int(quality.get("received_records", 0))
    valid = int(quality.get("valid_records", 0))
    rejected = int(quality.get("rejected_records", max(received - valid, 0)))
    return received, valid, rejected


class SnapshotIngestion:
    def __init__(self, ledger: Ledger, store: SnapshotStore) -> None:
        self.ledger = ledger
        self.store = store

    async def ingest(
        self,
        dataset: str,
        value: BaseModel | dict[str, Any],
    ) -> IngestionOutcome:
        payload = json_payload(value)
        digest = fingerprint(payload)
        idempotency_key = f"{dataset}:{digest}"
        run_id = await self.ledger.begin(dataset, idempotency_key)
        if run_id is None:
            object_key = await asyncio.to_thread(
                self.store.put_json,
                dataset,
                digest,
                payload,
            )
            return IngestionOutcome(dataset, "duplicate", idempotency_key, object_key)

        try:
            object_key = await asyncio.to_thread(self.store.put_json, dataset, digest, payload)
            received, valid, rejected = record_counts(payload)
            await self.ledger.complete(run_id, object_key, received, valid, rejected)
        except Exception as exc:
            await self.ledger.fail(run_id, str(exc))
            raise
        return IngestionOutcome(dataset, "completed", idempotency_key, object_key)
