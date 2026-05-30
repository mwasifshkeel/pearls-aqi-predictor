from __future__ import annotations

import datetime as dt
from typing import Iterable, List

import numpy as np
import pandas as pd


FIXED_PUBLIC_HOLIDAYS = {
    (8, 14),  # Independence Day
    (3, 23),  # Pakistan Day
    (5, 1),   # Labor Day
    (12, 25), # Quaid-e-Azam Day
}


def _is_public_holiday(ts: pd.Timestamp) -> int:
    return 1 if (ts.month, ts.day) in FIXED_PUBLIC_HOLIDAYS else 0


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    ts = pd.to_datetime(out["timestamp"], utc=True)
    out["hour_of_day"] = ts.dt.hour
    out["day_of_week"] = ts.dt.dayofweek
    out["day_of_month"] = ts.dt.day
    out["month"] = ts.dt.month
    out["quarter"] = ts.dt.quarter
    out["is_weekend"] = (out["day_of_week"] >= 5).astype(int)
    out["is_morning_rush"] = out["hour_of_day"].between(7, 9).astype(int)
    out["is_evening_rush"] = out["hour_of_day"].between(17, 19).astype(int)
    out["season"] = ((out["month"] % 12) // 3).astype(int)

    out["hour_sin"] = np.sin(2 * np.pi * out["hour_of_day"] / 24)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour_of_day"] / 24)
    out["day_of_week_sin"] = np.sin(2 * np.pi * out["day_of_week"] / 7)
    out["day_of_week_cos"] = np.cos(2 * np.pi * out["day_of_week"] / 7)
    out["month_sin"] = np.sin(2 * np.pi * out["month"] / 12)
    out["month_cos"] = np.cos(2 * np.pi * out["month"] / 12)
    day_of_year = ts.dt.dayofyear
    out["day_of_year_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
    out["day_of_year_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)

    out["is_pakistan_public_holiday"] = ts.apply(_is_public_holiday).astype(int)

    # Days since last rain based on precipitation column
    if "precipitation" in out:
        precip = out["precipitation"].fillna(0)
        days_since = []
        last_rain = None
        for idx, value in enumerate(precip):
            if value > 0:
                last_rain = idx
                days_since.append(0)
            else:
                if last_rain is None:
                    days_since.append(np.nan)
                else:
                    hours_since = idx - last_rain
                    days_since.append(hours_since / 24)
        out["days_since_last_rain"] = days_since
    else:
        out["days_since_last_rain"] = np.nan

    return out
