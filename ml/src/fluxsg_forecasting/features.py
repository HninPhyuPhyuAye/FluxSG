from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd

REGIONS = ("central", "east", "north", "south", "west")
TARGET_COLUMN = "target_psi_1h"
PSI_COLUMN = "psi_twenty_four_hourly"
SEASONAL_COLUMN = "psi_lag_24h"

POLLUTANT_COLUMNS = (
    PSI_COLUMN,
    "pm25_twenty_four_hourly",
    "pm10_twenty_four_hourly",
    "o3_eight_hour_max",
    "co_eight_hour_max",
    "so2_twenty_four_hourly",
    "no2_one_hour_max",
)
LAGS = (1, 2, 3, 6, 12, 24, 48, 168)
ROLLING_WINDOWS = (3, 6, 12, 24)
CYCLICAL_COLUMNS = ("hour_sin", "hour_cos", "dow_sin", "dow_cos")

FEATURE_COLUMNS = (
    *POLLUTANT_COLUMNS,
    *(f"psi_lag_{lag}h" for lag in LAGS),
    *(
        name
        for window in ROLLING_WINDOWS
        for name in (f"psi_roll_mean_{window}h", f"psi_roll_std_{window}h")
    ),
    *CYCLICAL_COLUMNS,
    *(f"region_{region}" for region in REGIONS),
)

REQUIRED_COLUMNS = {"timestamp", "region", *POLLUTANT_COLUMNS}


def load_history(paths: Iterable[Path]) -> pd.DataFrame:
    selected = sorted(Path(path) for path in paths)
    if not selected:
        raise ValueError("No historical CSV files were supplied")
    frames = [pd.read_csv(path) for path in selected]
    history = pd.concat(frames, ignore_index=True)
    missing = REQUIRED_COLUMNS.difference(history.columns)
    if missing:
        raise ValueError(f"Historical data is missing columns: {sorted(missing)}")

    return normalise_history(history)


def normalise_history(history: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS.difference(history.columns)
    if missing:
        raise ValueError(f"Historical data is missing columns: {sorted(missing)}")
    history = history.loc[history["region"].isin(REGIONS)].copy()
    history["timestamp"] = pd.to_datetime(
        history["timestamp"], utc=True, errors="coerce", format="mixed"
    )
    for column in POLLUTANT_COLUMNS:
        history[column] = pd.to_numeric(history[column], errors="coerce")
    history = history.dropna(subset=["timestamp", "region", PSI_COLUMN])
    return history.sort_values(["timestamp", "region"]).reset_index(drop=True)


def _hourly_panel(history: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for region, group in history.groupby("region", sort=True):
        hourly = (
            group.sort_values("timestamp")
            .drop_duplicates("timestamp", keep="last")
            .set_index("timestamp")
            .asfreq("h")
        )
        hourly["region"] = region
        frames.append(hourly)
    if not frames:
        raise ValueError("No recognised Singapore regions were present")
    return pd.concat(frames).sort_index().reset_index()


def build_features(history: pd.DataFrame, *, labelled_only: bool = True) -> pd.DataFrame:
    featured = _hourly_panel(normalise_history(history))
    grouped = featured.groupby("region", sort=False)[PSI_COLUMN]

    for lag in LAGS:
        featured[f"psi_lag_{lag}h"] = grouped.shift(lag)
    for window in ROLLING_WINDOWS:
        featured[f"psi_roll_mean_{window}h"] = grouped.transform(
            lambda values, size=window: values.rolling(size, min_periods=size).mean()
        )
        featured[f"psi_roll_std_{window}h"] = grouped.transform(
            lambda values, size=window: values.rolling(size, min_periods=size).std()
        )

    featured[TARGET_COLUMN] = grouped.shift(-1)
    hour = featured["timestamp"].dt.hour
    day_of_week = featured["timestamp"].dt.dayofweek
    featured["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    featured["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    featured["dow_sin"] = np.sin(2 * np.pi * day_of_week / 7)
    featured["dow_cos"] = np.cos(2 * np.pi * day_of_week / 7)
    for region in REGIONS:
        featured[f"region_{region}"] = (featured["region"] == region).astype(float)

    required = [PSI_COLUMN, SEASONAL_COLUMN]
    if labelled_only:
        required.append(TARGET_COLUMN)
    return featured.dropna(subset=required).reset_index(drop=True)


def chronological_split(
    frame: pd.DataFrame,
    *,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if train_fraction <= 0 or validation_fraction <= 0:
        raise ValueError("Split fractions must be positive")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("The test split must contain observations")

    timestamps = np.sort(frame["timestamp"].dropna().unique())
    if len(timestamps) < 10:
        raise ValueError("At least ten unique timestamps are required")
    train_end = timestamps[int(len(timestamps) * train_fraction)]
    validation_end = timestamps[int(len(timestamps) * (train_fraction + validation_fraction))]
    train = frame.loc[frame["timestamp"] < train_end].copy()
    validation = frame.loc[
        (frame["timestamp"] >= train_end) & (frame["timestamp"] < validation_end)
    ].copy()
    test = frame.loc[frame["timestamp"] >= validation_end].copy()
    if train.empty or validation.empty or test.empty:
        raise ValueError("Chronological split produced an empty partition")
    return train, validation, test


def fill_features(frame: pd.DataFrame, medians: pd.Series) -> pd.DataFrame:
    return frame.loc[:, FEATURE_COLUMNS].fillna(medians).fillna(0.0)
