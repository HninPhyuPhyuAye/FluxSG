import json
import os
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import joblib
import numpy as np
import pandas as pd

from fluxsg_forecasting.drift import assess_drift
from fluxsg_forecasting.features import (
    POLLUTANT_COLUMNS,
    PSI_COLUMN,
    REGIONS,
    build_features,
    fill_features,
    normalise_history,
)
from fluxsg_forecasting.metrics import psi_band

REALTIME_PSI_URL = "https://api-open.data.gov.sg/v2/real-time/api/psi"
SINGAPORE = ZoneInfo("Asia/Singapore")


def _headers() -> dict[str, str]:
    headers = {"User-Agent": "FluxSG/0.6 production forecast publisher"}
    if key := os.getenv("DATA_GOV_SG_API_KEY"):
        headers["x-api-key"] = key
    return headers


def _request_page(
    client: httpx.Client,
    day: date,
    pagination_token: str | None = None,
) -> dict[str, Any]:
    params = {"date": day.isoformat()}
    if pagination_token:
        params["paginationToken"] = pagination_token
    for attempt in range(8):
        response = client.get(REALTIME_PSI_URL, params=params)
        if response.status_code != 429:
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 0:
                raise RuntimeError(payload.get("errorMsg") or "data.gov.sg returned an error")
            return payload
        retry_after = response.headers.get("retry-after")
        time.sleep(float(retry_after) if retry_after else min(2 ** (attempt + 1), 10))
    raise RuntimeError("data.gov.sg rate limit did not clear after retries")


def normalise_realtime_items(items: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in items:
        readings = item.get("readings", {})
        for region in REGIONS:
            row: dict[str, Any] = {"timestamp": item.get("timestamp"), "region": region}
            complete = True
            for column in POLLUTANT_COLUMNS:
                values = readings.get(column) or {}
                if region not in values:
                    complete = False
                    break
                row[column] = values[region]
            if complete:
                rows.append(row)
    if not rows:
        raise ValueError("The real-time PSI response contained no complete regional readings")
    return normalise_history(pd.DataFrame(rows)).drop_duplicates(["timestamp", "region"])


def fetch_recent_history(output: Path, *, lookback_days: int = 9) -> dict[str, Any]:
    if lookback_days < 8:
        raise ValueError("At least eight days are required for the 168-hour lag")
    today = datetime.now(SINGAPORE).date()
    start = today - timedelta(days=lookback_days - 1)
    items: list[dict[str, Any]] = []
    with httpx.Client(timeout=60, follow_redirects=True, headers=_headers()) as client:
        for offset in range(lookback_days):
            day = start + timedelta(days=offset)
            token: str | None = None
            while True:
                payload = _request_page(client, day, token)
                data = payload["data"]
                items.extend(data.get("items", []))
                token = data.get("paginationToken")
                if not token:
                    break

    history = normalise_realtime_items(items)
    output.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(output, index=False)
    return {
        "source": "data.gov.sg / National Environment Agency real-time PSI API",
        "source_url": REALTIME_PSI_URL,
        "path": str(output),
        "rows": len(history),
        "regions": sorted(history["region"].unique().tolist()),
        "start": history["timestamp"].min().isoformat(),
        "end": history["timestamp"].max().isoformat(),
    }


def _utc(value: str | pd.Timestamp | datetime) -> datetime:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(UTC)
    return timestamp.tz_convert(UTC).to_pydatetime()


def publish_forecast(
    *,
    recent_path: Path,
    model_path: Path,
    reference_path: Path,
    metrics_path: Path,
    output: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    generated_at = now or datetime.now(UTC)
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=UTC)
    generated_at = generated_at.astimezone(UTC)

    bundle = joblib.load(model_path)
    reference = json.loads(reference_path.read_text())
    metrics = json.loads(metrics_path.read_text())
    recent = normalise_history(pd.read_csv(recent_path))
    features = build_features(recent, labelled_only=False)
    latest = (
        features.sort_values("timestamp")
        .groupby("region", as_index=False)
        .tail(1)
        .sort_values("region")
        .copy()
    )
    medians = pd.Series(bundle["medians"])
    predictions = np.maximum(bundle["model"].predict(fill_features(latest, medians)), 0)
    radius = float(bundle["interval_radius"])
    observed_at = _utc(latest["timestamp"].max())
    trained_through = _utc(bundle["trained_through"])
    forecast_for = observed_at + timedelta(hours=1)
    freshness_hours = max((generated_at - observed_at).total_seconds() / 3600, 0)
    model_age_hours = max((generated_at - trained_through).total_seconds() / 3600, 0)
    drift_window = features.loc[
        features["timestamp"] >= features["timestamp"].max() - pd.Timedelta(days=7)
    ]
    drift = assess_drift(drift_window, reference)
    promotion = bundle["promotion"]
    coverage = float(metrics["uncertainty"]["coverage"])
    candidate_test_mae = float(metrics["test"]["candidate"]["mae"])
    persistence_test_mae = float(metrics["test"]["persistence"]["mae"])
    region_complete = set(latest["region"]) == set(REGIONS)
    checks = {
        "source_fresh": freshness_hours <= 3,
        "all_regions_present": region_complete,
        "model_recent": model_age_hours <= 72,
        "offline_promotion_passed": promotion["status"] == "promoted",
        "heldout_beats_persistence": candidate_test_mae < persistence_test_mae,
        "drift_clear": drift["status"] != "alert",
        "interval_coverage_acceptable": coverage >= 0.85,
    }
    available = all(checks.values())
    failure_reasons = {
        "source_fresh": "the source observation is stale",
        "all_regions_present": "one or more regions are missing",
        "model_recent": "the model training window is stale",
        "offline_promotion_passed": "the candidate failed the promotion rule",
        "heldout_beats_persistence": "the candidate did not beat persistence on holdout data",
        "drift_clear": "live inputs triggered a distribution-drift alert",
        "interval_coverage_acceptable": "prediction-interval coverage is below 85%",
    }
    failed = [failure_reasons[name] for name, passed in checks.items() if not passed]
    reason = (
        "All release guardrails passed. Treat these values as estimates beside official readings."
        if available
        else "Forecast withheld because " + "; ".join(failed) + "."
    )

    records = []
    bands = psi_band(predictions)
    for (_, row), prediction, band in zip(latest.iterrows(), predictions, bands, strict=True):
        records.append(
            {
                "region": row["region"],
                "observed_psi_24h": round(float(row[PSI_COLUMN]), 1),
                "predicted_psi_24h": round(float(prediction), 1),
                "lower_90": round(max(float(prediction) - radius, 0), 1),
                "upper_90": round(float(prediction) + radius, 1),
                "predicted_band": str(band),
            }
        )

    result = {
        "schema_version": 1,
        "forecast_type": "regional 24-hour PSI one hour ahead",
        "source": "data.gov.sg / National Environment Agency",
        "source_url": REALTIME_PSI_URL,
        "generated_at": generated_at.isoformat(),
        "observed_at": observed_at.isoformat(),
        "forecast_for": forecast_for.isoformat(),
        "expires_at": (observed_at + timedelta(hours=3)).isoformat(),
        "available": available,
        "status": "available" if available else "withheld",
        "reason": reason,
        "checks": checks,
        "freshness_hours": round(freshness_hours, 2),
        "model": {
            "name": "histogram gradient boosting",
            "version": "psi-hgb-v1",
            "trained_through": trained_through.isoformat(),
            "age_hours": round(model_age_hours, 2),
            "test_mae": candidate_test_mae,
            "persistence_mae": persistence_test_mae,
            "interval_coverage": coverage,
            "backtest_wins": promotion["backtest_wins"],
            "backtest_folds": promotion["backtest_folds"],
        },
        "drift": drift,
        "forecasts": records,
        "disclaimer": (
            "Experimental estimate, not official guidance. Use current NEA observations and "
            "haze.gov.sg advice for health and operational decisions."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result
