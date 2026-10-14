import numpy as np
import pandas as pd
import pytest

from fluxsg_forecasting.features import REGIONS


@pytest.fixture
def hourly_history() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01", periods=600, freq="h", tz="Asia/Singapore")
    rows = []
    for region_index, region in enumerate(REGIONS):
        for index, timestamp in enumerate(timestamps):
            daily = 5 * np.sin(2 * np.pi * index / 24)
            weekly = 2 * np.sin(2 * np.pi * index / 168)
            psi = 45 + region_index * 2 + daily + weekly + index * 0.005
            rows.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "region": region,
                    "psi_twenty_four_hourly": round(psi, 2),
                    "pm25_twenty_four_hourly": round(psi * 0.35, 2),
                    "pm10_twenty_four_hourly": round(psi * 0.7, 2),
                    "o3_eight_hour_max": round(30 + daily, 2),
                    "co_eight_hour_max": round(0.3 + region_index * 0.01, 2),
                    "so2_twenty_four_hourly": round(3 + weekly / 2, 2),
                    "no2_one_hour_max": round(10 + daily / 2, 2),
                }
            )
    return pd.DataFrame(rows)
