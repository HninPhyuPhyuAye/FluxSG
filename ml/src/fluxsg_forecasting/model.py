import hashlib
import json
import os
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor

from fluxsg_forecasting.drift import assess_drift, build_reference
from fluxsg_forecasting.features import (
    FEATURE_COLUMNS,
    PSI_COLUMN,
    REGIONS,
    SEASONAL_COLUMN,
    TARGET_COLUMN,
    build_features,
    chronological_split,
    fill_features,
    load_history,
)
from fluxsg_forecasting.metrics import interval_metrics, psi_band, regression_metrics


def new_model(max_iter: int = 250) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        learning_rate=0.05,
        max_iter=max_iter,
        max_leaf_nodes=15,
        l2_regularization=1.0,
        random_state=42,
    )


def _git_sha() -> str | None:
    supplied = os.getenv("GIT_SHA")
    if supplied and supplied != "unknown":
        return supplied
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _file_fingerprints(paths: list[Path]) -> list[dict[str, Any]]:
    return [
        {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(paths)
    ]


def _partition_summary(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": len(frame),
        "timestamps": int(frame["timestamp"].nunique()),
        "start": frame["timestamp"].min().isoformat(),
        "end": frame["timestamp"].max().isoformat(),
    }


def _backtests(
    frame: pd.DataFrame,
    *,
    folds: int,
    max_iter: int,
) -> list[dict[str, Any]]:
    timestamps = np.sort(frame["timestamp"].unique())
    initial_fraction = 0.50
    step = (0.40 / folds) if folds else 0
    reports: list[dict[str, Any]] = []
    for fold in range(folds):
        train_end_index = int(len(timestamps) * (initial_fraction + fold * step))
        test_end_index = int(len(timestamps) * (initial_fraction + (fold + 1) * step))
        train_end = timestamps[train_end_index]
        test_end = timestamps[min(test_end_index, len(timestamps) - 1)]
        train = frame.loc[frame["timestamp"] < train_end]
        test = frame.loc[(frame["timestamp"] >= train_end) & (frame["timestamp"] < test_end)]
        medians = train.loc[:, FEATURE_COLUMNS].median()
        estimator = new_model(max_iter=max_iter)
        estimator.fit(fill_features(train, medians), train[TARGET_COLUMN])
        candidate = estimator.predict(fill_features(test, medians))
        reports.append(
            {
                "fold": fold + 1,
                "train_end": train["timestamp"].max().isoformat(),
                "test_start": test["timestamp"].min().isoformat(),
                "test_end": test["timestamp"].max().isoformat(),
                "rows": len(test),
                "candidate": regression_metrics(test[TARGET_COLUMN], candidate),
                "persistence": regression_metrics(test[TARGET_COLUMN], test[PSI_COLUMN]),
                "seasonal_24h": regression_metrics(test[TARGET_COLUMN], test[SEASONAL_COLUMN]),
            }
        )
    return reports


def _latest_forecasts(
    feature_frame: pd.DataFrame,
    *,
    estimator: HistGradientBoostingRegressor,
    medians: pd.Series,
    interval_radius: float,
) -> pd.DataFrame:
    latest = (
        feature_frame.sort_values("timestamp")
        .groupby("region", as_index=False)
        .tail(1)
        .sort_values("region")
        .copy()
    )
    predictions = np.maximum(estimator.predict(fill_features(latest, medians)), 0)
    latest["forecast_for"] = latest["timestamp"] + pd.Timedelta(hours=1)
    latest["predicted_psi_24h"] = np.round(predictions, 1)
    latest["lower_90"] = np.round(np.maximum(predictions - interval_radius, 0), 1)
    latest["upper_90"] = np.round(predictions + interval_radius, 1)
    latest["predicted_band"] = psi_band(predictions)
    return latest.loc[
        :,
        [
            "region",
            "timestamp",
            "forecast_for",
            PSI_COLUMN,
            "predicted_psi_24h",
            "lower_90",
            "upper_90",
            "predicted_band",
        ],
    ]


def run_experiment(
    input_paths: list[Path],
    output_dir: Path,
    *,
    max_iter: int = 250,
    backtest_folds: int = 4,
) -> dict[str, Any]:
    started_at = datetime.now(UTC)
    history = load_history(input_paths)
    labelled = build_features(history)
    all_features = build_features(history, labelled_only=False)
    train, validation, test = chronological_split(labelled)

    medians = train.loc[:, FEATURE_COLUMNS].median()
    evaluation_model = new_model(max_iter=max_iter)
    evaluation_model.fit(fill_features(train, medians), train[TARGET_COLUMN])
    validation_prediction = evaluation_model.predict(fill_features(validation, medians))
    test_prediction = evaluation_model.predict(fill_features(test, medians))

    validation_metrics = {
        "candidate": regression_metrics(validation[TARGET_COLUMN], validation_prediction),
        "persistence": regression_metrics(validation[TARGET_COLUMN], validation[PSI_COLUMN]),
        "seasonal_24h": regression_metrics(validation[TARGET_COLUMN], validation[SEASONAL_COLUMN]),
    }
    test_metrics = {
        "candidate": regression_metrics(test[TARGET_COLUMN], test_prediction),
        "persistence": regression_metrics(test[TARGET_COLUMN], test[PSI_COLUMN]),
        "seasonal_24h": regression_metrics(test[TARGET_COLUMN], test[SEASONAL_COLUMN]),
    }
    calibration_errors = np.abs(validation[TARGET_COLUMN].to_numpy() - validation_prediction)
    interval_radius = float(np.quantile(calibration_errors, 0.90, method="higher"))
    lower = np.maximum(test_prediction - interval_radius, 0)
    upper = test_prediction + interval_radius

    predictions = test.loc[:, ["timestamp", "region", TARGET_COLUMN, PSI_COLUMN]].copy()
    predictions["candidate_prediction"] = np.round(test_prediction, 4)
    predictions["persistence_prediction"] = predictions[PSI_COLUMN]
    predictions["seasonal_prediction"] = test[SEASONAL_COLUMN].to_numpy()
    predictions["lower_90"] = np.round(lower, 4)
    predictions["upper_90"] = np.round(upper, 4)

    reference = build_reference(train)
    drift_report = assess_drift(test, reference)
    backtests = _backtests(labelled, folds=backtest_folds, max_iter=max_iter)
    strongest_baseline = min(
        validation_metrics["persistence"]["mae"], validation_metrics["seasonal_24h"]["mae"]
    )
    backtest_wins = sum(fold["candidate"]["mae"] < fold["persistence"]["mae"] for fold in backtests)
    required_backtest_wins = (backtest_folds // 2) + 1 if backtest_folds else 0
    promoted = (
        validation_metrics["candidate"]["mae"] < strongest_baseline
        and backtest_wins >= required_backtest_wins
    )

    production_medians = labelled.loc[:, FEATURE_COLUMNS].median()
    production_model = new_model(max_iter=max_iter)
    production_model.fit(fill_features(labelled, production_medians), labelled[TARGET_COLUMN])
    latest_forecasts = _latest_forecasts(
        all_features,
        estimator=production_model,
        medians=production_medians,
        interval_radius=interval_radius,
    )

    completed_at = datetime.now(UTC)
    report: dict[str, Any] = {
        "experiment": "regional_psi_24h_one_hour_ahead",
        "generated_at": completed_at.isoformat(),
        "duration_seconds": round((completed_at - started_at).total_seconds(), 3),
        "target": "regional 24-hour PSI one hour ahead",
        "source": "data.gov.sg / National Environment Agency historical PSI",
        "regions": list(REGIONS),
        "rows": len(labelled),
        "partitions": {
            "train": _partition_summary(train),
            "validation": _partition_summary(validation),
            "test": _partition_summary(test),
        },
        "validation": validation_metrics,
        "test": test_metrics,
        "uncertainty": {
            "method": "symmetric validation-residual interval",
            "nominal_coverage": 0.90,
            "radius_psi": round(interval_radius, 4),
            **interval_metrics(test[TARGET_COLUMN], lower, upper),
        },
        "promotion": {
            "status": "promoted" if promoted else "rejected",
            "rule": (
                "candidate validation MAE must beat both persistence and 24-hour seasonal "
                "baselines, and win a majority of backtests"
            ),
            "backtest_wins": backtest_wins,
            "backtest_folds": backtest_folds,
            "strongest_baseline_mae": strongest_baseline,
            "candidate_mae": validation_metrics["candidate"]["mae"],
            "improvement_percent": round(
                (strongest_baseline - validation_metrics["candidate"]["mae"])
                / strongest_baseline
                * 100,
                2,
            ),
        },
        "backtests": backtests,
        "drift": drift_report,
        "reproducibility": {
            "git_sha": _git_sha(),
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "random_state": 42,
            "inputs": _file_fingerprints(input_paths),
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    (output_dir / "training_reference.json").write_text(json.dumps(reference, indent=2) + "\n")
    (output_dir / "drift_report.json").write_text(json.dumps(drift_report, indent=2) + "\n")
    predictions.to_csv(output_dir / "test_predictions.csv", index=False)
    latest_forecasts.to_csv(output_dir / "latest_forecast.csv", index=False)
    joblib.dump(
        {
            "model": production_model,
            "feature_columns": list(FEATURE_COLUMNS),
            "medians": production_medians,
            "interval_radius": interval_radius,
            "trained_through": labelled["timestamp"].max().isoformat(),
            "promotion": report["promotion"],
        },
        output_dir / "model.joblib",
    )
    return report
