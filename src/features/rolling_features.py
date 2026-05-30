from __future__ import annotations

from typing import List

import pandas as pd


ROLLING_WINDOWS = [3, 6, 12, 24, 48, 168]
ROLLING_BASE_VARS = [
    "european_aqi",
    "pm2_5",
    "pm10",
    "wind_speed_10m",
    "relative_humidity_2m",
]


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in ROLLING_BASE_VARS:
        if column not in out:
            continue
        for window in ROLLING_WINDOWS:
            rolling = out[column].rolling(window=window, min_periods=1)
            out[f"{column}_rolling_mean_{window}h"] = rolling.mean()
            out[f"{column}_rolling_std_{window}h"] = rolling.std()
            out[f"{column}_rolling_min_{window}h"] = rolling.min()
    return out
