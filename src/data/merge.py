from __future__ import annotations

import pandas as pd


def merge_weather_aq(weather_df: pd.DataFrame, aq_df: pd.DataFrame) -> pd.DataFrame:
    """Align weather and air quality on hourly timestamp."""
    if "timestamp" not in weather_df or "timestamp" not in aq_df:
        raise ValueError("Both frames must include timestamp column")
    merged = pd.merge(weather_df, aq_df, on="timestamp", how="outer")
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    return merged
