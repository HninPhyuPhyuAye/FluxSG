from typing import Any

import numpy as np
import pandas as pd

DRIFT_FEATURES = (
    "psi_twenty_four_hourly",
    "pm25_twenty_four_hourly",
    "pm10_twenty_four_hourly",
    "o3_eight_hour_max",
)
EPSILON = 1e-6


def build_reference(frame: pd.DataFrame) -> dict[str, Any]:
    features: dict[str, Any] = {}
    for column in DRIFT_FEATURES:
        values = frame[column].dropna().to_numpy(dtype=float)
        edges = np.unique(np.quantile(values, np.linspace(0, 1, 11)))
        if len(edges) < 3:
            edges = np.array([values.min() - 1, values.mean(), values.max() + 1])
        edges[0], edges[-1] = -np.inf, np.inf
        counts, _ = np.histogram(values, bins=edges)
        expected = np.maximum(counts / counts.sum(), EPSILON)
        features[column] = {
            "bin_edges": [None if np.isinf(value) else float(value) for value in edges],
            "expected_proportions": expected.tolist(),
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
        }
    return {"features": features, "warning_threshold": 0.1, "alert_threshold": 0.25}


def _restore_edges(values: list[float | None]) -> np.ndarray:
    restored = np.array(
        [
            -np.inf if index == 0 and value is None else np.inf if value is None else value
            for index, value in enumerate(values)
        ],
        dtype=float,
    )
    return restored


def assess_drift(frame: pd.DataFrame, reference: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    overall = "healthy"
    for column, profile in reference["features"].items():
        values = frame[column].dropna().to_numpy(dtype=float)
        edges = _restore_edges(profile["bin_edges"])
        actual_counts, _ = np.histogram(values, bins=edges)
        actual = np.maximum(actual_counts / max(actual_counts.sum(), 1), EPSILON)
        expected = np.maximum(np.asarray(profile["expected_proportions"]), EPSILON)
        population_stability_index = float(np.sum((actual - expected) * np.log(actual / expected)))
        std = max(float(profile["std"]), EPSILON)
        standardised_mean_shift = abs(float(np.mean(values)) - float(profile["mean"])) / std
        if population_stability_index >= reference["alert_threshold"]:
            status = "alert"
            overall = "alert"
        elif population_stability_index >= reference["warning_threshold"]:
            status = "warning"
            if overall == "healthy":
                overall = "warning"
        else:
            status = "healthy"
        results[column] = {
            "population_stability_index": round(population_stability_index, 4),
            "standardised_mean_shift": round(standardised_mean_shift, 4),
            "status": status,
        }
    return {"status": overall, "rows_evaluated": len(frame), "features": results}
