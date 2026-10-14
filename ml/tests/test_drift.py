import pandas as pd

from fluxsg_forecasting.drift import assess_drift, build_reference
from fluxsg_forecasting.features import build_features


def test_identical_distribution_is_healthy(hourly_history: pd.DataFrame) -> None:
    features = build_features(hourly_history)
    reference = build_reference(features)

    report = assess_drift(features.copy(), reference)

    assert report["status"] == "healthy"
    assert all(item["population_stability_index"] == 0 for item in report["features"].values())


def test_shifted_distribution_raises_alert(hourly_history: pd.DataFrame) -> None:
    features = build_features(hourly_history)
    reference = build_reference(features)
    shifted = features.copy()
    for column in reference["features"]:
        shifted[column] = shifted[column] + 100

    report = assess_drift(shifted, reference)

    assert report["status"] == "alert"
