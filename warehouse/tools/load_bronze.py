import argparse
import hashlib
import json
import os
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import psycopg2
from minio import Minio

BOOTSTRAP_SQL = """
CREATE SCHEMA IF NOT EXISTS bronze;

CREATE TABLE IF NOT EXISTS bronze.raw_snapshots (
    snapshot_id TEXT NOT NULL,
    dataset TEXT NOT NULL,
    object_key TEXT NOT NULL UNIQUE,
    source_name TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL,
    source_updated_at TIMESTAMPTZ,
    received_records INTEGER NOT NULL CHECK (received_records >= 0),
    valid_records INTEGER NOT NULL CHECK (valid_records >= 0),
    rejected_records INTEGER NOT NULL CHECK (rejected_records >= 0),
    payload JSONB NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (dataset, snapshot_id),
    CHECK (valid_records + rejected_records <= received_records)
);

CREATE INDEX IF NOT EXISTS raw_snapshots_dataset_ingested_idx
    ON bronze.raw_snapshots (dataset, ingested_at DESC);

CREATE TABLE IF NOT EXISTS bronze.quarantine_records (
    quarantine_id TEXT PRIMARY KEY,
    dataset TEXT NOT NULL,
    object_key TEXT NOT NULL,
    source_name TEXT NOT NULL,
    record JSONB NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (object_key, quarantine_id)
);

CREATE INDEX IF NOT EXISTS quarantine_records_dataset_loaded_idx
    ON bronze.quarantine_records (dataset, loaded_at DESC);
"""


def stable_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def parse_timestamp(value: Any) -> datetime:
    if not value:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(str(value))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def quality_counts(payload: dict[str, Any]) -> tuple[int, int, int]:
    quality = payload.get("quality", {})
    received = int(quality.get("received_records", 0))
    valid = int(quality.get("valid_records", 0))
    rejected = int(quality.get("rejected_records", max(received - valid, 0)))
    return received, valid, rejected


def postgres_connection():  # type: ignore[no-untyped-def]
    return psycopg2.connect(
        host=os.getenv("DBT_HOST", "127.0.0.1"),
        port=int(os.getenv("DBT_PORT", "5432")),
        user=os.getenv("DBT_USER", "fluxsg"),
        password=os.getenv("DBT_PASSWORD", "fluxsg-local"),
        dbname=os.getenv("DBT_DATABASE", "fluxsg"),
    )


def s3_client() -> tuple[Minio, str]:
    endpoint = os.getenv("OBJECT_STORE_ENDPOINT", "http://127.0.0.1:8333")
    parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
    client = Minio(
        parsed.netloc or parsed.path,
        access_key=os.getenv("OBJECT_STORE_ACCESS_KEY", "fluxsg"),
        secret_key=os.getenv("OBJECT_STORE_SECRET_KEY", "fluxsg-local-secret"),
        secure=os.getenv("OBJECT_STORE_SECURE", "false").lower() == "true",
    )
    return client, os.getenv("OBJECT_STORE_BUCKET", "fluxsg-raw")


def s3_documents(prefix: str) -> Iterable[tuple[str, str, dict[str, Any]]]:
    client, bucket = s3_client()
    for item in client.list_objects(bucket, prefix=prefix, recursive=True):
        if not item.object_name.endswith(".json"):
            continue
        response = client.get_object(bucket, item.object_name)
        try:
            payload = json.load(response)
        finally:
            response.close()
            response.release_conn()
        parts = item.object_name.split("/")
        yield parts[1], item.object_name, payload


def fixture_documents(
    root: Path, kind: str
) -> Iterable[tuple[str, str, dict[str, Any]]]:
    base = root / kind
    if not base.exists():
        return
    for path in sorted(base.glob("*/*.json")):
        payload = json.loads(path.read_text())
        digest = hashlib.sha256(stable_json(payload)).hexdigest()
        dataset = path.parent.name
        yield dataset, f"{kind}/{dataset}/fixture/{digest}.json", payload


def insert_snapshot(
    cursor, dataset: str, object_key: str, payload: dict[str, Any]
) -> int:  # type: ignore[no-untyped-def]
    digest = Path(object_key).stem
    if len(digest) != 64:
        digest = hashlib.sha256(stable_json(payload)).hexdigest()
    received, valid, rejected = quality_counts(payload)
    source_updated = (
        payload.get("source_updated_at")
        or payload.get("updated_at")
        or payload.get("observed_at")
    )
    cursor.execute(
        """
        INSERT INTO bronze.raw_snapshots (
            snapshot_id, dataset, object_key, source_name, ingested_at,
            source_updated_at, received_records, valid_records, rejected_records, payload
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT DO NOTHING
        """,
        (
            digest,
            dataset,
            object_key,
            str(payload.get("source", dataset)),
            parse_timestamp(payload.get("ingested_at")),
            parse_timestamp(source_updated) if source_updated else None,
            received,
            valid,
            rejected,
            stable_json(payload).decode(),
        ),
    )
    return cursor.rowcount


def insert_quarantine(
    cursor,
    dataset: str,
    object_key: str,
    payload: dict[str, Any],  # type: ignore[no-untyped-def]
) -> int:
    inserted = 0
    for index, item in enumerate(payload.get("rejected_records", [])):
        quarantine_id = hashlib.sha256(f"{object_key}:{index}".encode()).hexdigest()
        cursor.execute(
            """
            INSERT INTO bronze.quarantine_records (
                quarantine_id, dataset, object_key, source_name, record
            ) VALUES (%s, %s, %s, %s, %s::jsonb)
            ON CONFLICT DO NOTHING
            """,
            (
                quarantine_id,
                dataset,
                object_key,
                str(item.get("source", "root")) if isinstance(item, dict) else "root",
                json.dumps(
                    item.get("record", item) if isinstance(item, dict) else item
                ),
            ),
        )
        inserted += cursor.rowcount
    return inserted


def load(fixture_dir: Path | None) -> dict[str, int]:
    raw_documents = (
        fixture_documents(fixture_dir, "raw") if fixture_dir else s3_documents("raw/")
    )
    quarantine_documents = (
        fixture_documents(fixture_dir, "quarantine")
        if fixture_dir
        else s3_documents("quarantine/")
    )
    counts = {"snapshots_inserted": 0, "quarantine_records_inserted": 0}
    with postgres_connection() as connection, connection.cursor() as cursor:
        cursor.execute(BOOTSTRAP_SQL)
        for dataset, object_key, payload in raw_documents:
            counts["snapshots_inserted"] += insert_snapshot(
                cursor, dataset, object_key, payload
            )
        for dataset, object_key, payload in quarantine_documents:
            counts["quarantine_records_inserted"] += insert_quarantine(
                cursor, dataset, object_key, payload
            )
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load FluxSG bronze snapshots")
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        help="Load deterministic local fixtures instead of the S3-compatible object store",
    )
    arguments = parser.parse_args()
    print(json.dumps(load(arguments.fixture_dir), sort_keys=True))
