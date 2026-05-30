from __future__ import annotations

from typing import Dict, Iterable, List

import pandas as pd


LAG_CONFIG = {
    "european_aqi": [1, 2, 3, 6, 12, 24, 48, 72, 168],
    "pm2_5": [1, 6, 24, 48, 168],
    "pm10": [1, 6, 24, 48, 168],
    "nitrogen_dioxide": [1, 6, 24],
    "wind_speed_10m": [1, 3, 6, 24],
    "temperature_2m": [1, 3, 6],
}


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column, lags in LAG_CONFIG.items():
        if column not in out:
            continue
        for lag in lags:
            out[f"{column}_lag_{lag}h"] = out[column].shift(lag)
    return out
