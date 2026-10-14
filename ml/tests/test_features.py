import pandas as pd

from fluxsg_forecasting.features import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_features,
    chronological_split,
    normalise_history,
)


def test_features_use_the_next_hour_as_target(hourly_history: pd.DataFrame) -> None:
    featured = build_features(hourly_history)
    central = featured.loc[featured["region"] == "central"].sort_values("timestamp")

    first = central.iloc[0]
    source = hourly_history.copy()
    source["timestamp"] = pd.to_datetime(source["timestamp"], utc=True)
    expected = source.loc[
        (source["region"] == "central")
        & (source["timestamp"] == first["timestamp"] + pd.Timedelta(hours=1)),
        "psi_twenty_four_hourly",
    ].iloc[0]

    assert first[TARGET_COLUMN] == expected
    assert set(FEATURE_COLUMNS).issubset(featured.columns)


def test_chronological_split_has_no_time_overlap(hourly_history: pd.DataFrame) -> None:
    train, validation, test = chronological_split(build_features(hourly_history))

    assert train["timestamp"].max() < validation["timestamp"].min()
    assert validation["timestamp"].max() < test["timestamp"].min()
    assert len(train) > len(validation)
    assert len(test) > 0


def test_normalisation_accepts_mixed_iso_timestamp_formats(
    hourly_history: pd.DataFrame,
) -> None:
    mixed = hourly_history.iloc[:2].copy()
    mixed.loc[mixed.index[0], "timestamp"] = "2026-10-14T10:00:00+08:00"
    mixed.loc[mixed.index[1], "timestamp"] = "2026-10-14 02:00:00+00:00"

    result = normalise_history(mixed)

    assert len(result) == 2
    assert result["timestamp"].notna().all()
