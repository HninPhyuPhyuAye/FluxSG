from typing import Any

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error


def psi_band(values: np.ndarray) -> np.ndarray:
    bins = np.array([50, 100, 200, 300])
    labels = np.array(["Good", "Moderate", "Unhealthy", "Very Unhealthy", "Hazardous"])
    return labels[np.digitize(values, bins, right=True)]


def regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    actual_values = np.asarray(actual, dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)
    return {
        "mae": round(float(mean_absolute_error(actual_values, predicted_values)), 4),
        "rmse": round(float(mean_squared_error(actual_values, predicted_values) ** 0.5), 4),
        "band_accuracy": round(
            float(np.mean(psi_band(actual_values) == psi_band(predicted_values))), 4
        ),
    }


def interval_metrics(actual: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> dict[str, Any]:
    actual_values = np.asarray(actual, dtype=float)
    lower_values = np.asarray(lower, dtype=float)
    upper_values = np.asarray(upper, dtype=float)
    return {
        "coverage": round(
            float(np.mean((actual_values >= lower_values) & (actual_values <= upper_values))),
            4,
        ),
        "mean_width": round(float(np.mean(upper_values - lower_values)), 4),
    }
