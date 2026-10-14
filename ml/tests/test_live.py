from datetime import timedelta
from pathlib import Path

import pandas as pd

from fluxsg_forecasting.features import POLLUTANT_COLUMNS, REGIONS
from fluxsg_forecasting.live import normalise_realtime_items, publish_forecast
from fluxsg_forecasting.model import run_experiment


def test_normalises_complete_realtime_regions() -> None:
    readings = {
        column: {region: 40 + index for index, region in enumerate(REGIONS)}
        for column in POLLUTANT_COLUMNS
    }

    result = normalise_realtime_items(
        [{"timestamp": "2026-10-14T10:00:00+08:00", "readings": readings}]
    )

    assert len(result) == 5
    assert set(result["region"]) == set(REGIONS)
    assert str(result["timestamp"].dt.tz) == "UTC"


def test_publisher_exposes_guardrail_decision(hourly_history: pd.DataFrame, tmp_path: Path) -> None:
    input_path = tmp_path / "history.csv"
    artifacts = tmp_path / "artifacts"
    output = tmp_path / "forecast.json"
    hourly_history.to_csv(input_path, index=False)
    run_experiment([input_path], artifacts, max_iter=20, backtest_folds=1)
    latest = pd.to_datetime(hourly_history["timestamp"], utc=True).max().to_pydatetime()

    result = publish_forecast(
        recent_path=input_path,
        model_path=artifacts / "model.joblib",
        reference_path=artifacts / "training_reference.json",
        metrics_path=artifacts / "metrics.json",
        output=output,
        now=latest + timedelta(hours=1),
    )

    assert output.exists()
    assert result["status"] in {"available", "withheld"}
    assert set(result["checks"]) == {
        "source_fresh",
        "all_regions_present",
        "model_recent",
        "offline_promotion_passed",
        "heldout_beats_persistence",
        "drift_clear",
        "interval_coverage_acceptable",
    }
    assert len(result["forecasts"]) == 5
    assert result["forecast_for"] > result["observed_at"]
