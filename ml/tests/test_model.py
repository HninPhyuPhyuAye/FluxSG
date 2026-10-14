from pathlib import Path

import pandas as pd

from fluxsg_forecasting.model import run_experiment


def test_experiment_writes_reproducible_artifacts(
    hourly_history: pd.DataFrame, tmp_path: Path
) -> None:
    input_path = tmp_path / "history.csv"
    output_dir = tmp_path / "run"
    hourly_history.to_csv(input_path, index=False)

    report = run_experiment([input_path], output_dir, max_iter=20, backtest_folds=1)

    assert report["partitions"]["train"]["end"] < report["partitions"]["validation"]["start"]
    assert report["partitions"]["validation"]["end"] < report["partitions"]["test"]["start"]
    assert report["uncertainty"]["mean_width"] >= 0
    assert report["promotion"]["status"] in {"promoted", "rejected"}
    for filename in (
        "metrics.json",
        "training_reference.json",
        "drift_report.json",
        "test_predictions.csv",
        "latest_forecast.csv",
        "model.joblib",
    ):
        assert (output_dir / filename).exists()
