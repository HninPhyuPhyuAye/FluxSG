import csv
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

DATASETS = {
    "2023": "d_10501b71361f97dbbbab82095406c9c5",
    "2024": "d_9213cd2e4631f7148ab5932a10df9958",
}
API_ROOT = "https://api-open.data.gov.sg/v1/public/api/datasets"


def _headers() -> dict[str, str]:
    headers = {"User-Agent": "FluxSG/0.5 forecasting pipeline"}
    if key := os.getenv("DATA_GOV_SG_API_KEY"):
        headers["x-api-key"] = key
    return headers


def _payload(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(payload.get("errorMsg") or "data.gov.sg returned an error")
    return payload


def _get_payload(client: httpx.Client, url: str) -> dict[str, Any]:
    for attempt in range(8):
        response = client.get(url)
        if response.status_code != 429:
            return _payload(response)
        retry_after = response.headers.get("retry-after")
        delay = float(retry_after) if retry_after else min(2 ** (attempt + 1), 10)
        time.sleep(delay)
    raise RuntimeError("data.gov.sg rate limit did not clear after retries")


def download_dataset(dataset_id: str, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=120, follow_redirects=True, headers=_headers()) as client:
        _get_payload(client, f"{API_ROOT}/{dataset_id}/initiate-download")
        download_url: str | None = None
        for attempt in range(8):
            result = _get_payload(client, f"{API_ROOT}/{dataset_id}/poll-download")["data"]
            if result.get("status") == "DOWNLOAD_SUCCESS" and result.get("url"):
                download_url = result["url"]
                break
            time.sleep(min(2**attempt, 10))
        if not download_url:
            raise RuntimeError(f"Dataset {dataset_id} was not ready after polling")
        response = client.get(download_url)
        response.raise_for_status()
        destination.write_bytes(response.content)

    with destination.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = sum(1 for _ in reader)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return {
        "dataset_id": dataset_id,
        "path": str(destination),
        "rows": rows,
        "sha256": digest,
    }


def fetch_history(output_dir: Path) -> dict[str, Any]:
    downloads = []
    for year, dataset_id in DATASETS.items():
        downloads.append(download_dataset(dataset_id, output_dir / f"nea-psi-{year}.csv"))
    manifest = {
        "provider": "data.gov.sg / National Environment Agency",
        "collection_id": "2215",
        "downloads": downloads,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
