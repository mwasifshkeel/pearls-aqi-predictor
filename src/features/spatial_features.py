from __future__ import annotations

import numpy as np
import pandas as pd


def add_spatial_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    wind_dir = out["wind_direction_10m"] if "wind_direction_10m" in out else None

    if wind_dir is not None:
        radians = np.deg2rad(wind_dir)
        out["wind_direction_sin"] = np.sin(radians)
        out["wind_direction_cos"] = np.cos(radians)
        out["wind_direction_quadrant"] = pd.cut(
            wind_dir % 360,
            bins=[-1, 45, 135, 225, 315, 361],
            labels=[0, 1, 2, 3, 0],
            ordered=False,
        ).astype(float)
        out["prevailing_wind_from_industrial"] = wind_dir.between(45, 135).astype(int)
        out["wind_direction_change_3h"] = wind_dir.diff(3).abs()
    else:
        out["wind_direction_sin"] = np.nan
        out["wind_direction_cos"] = np.nan
        out["wind_direction_quadrant"] = np.nan
        out["prevailing_wind_from_industrial"] = np.nan
        out["wind_direction_change_3h"] = np.nan

    temp = out["temperature_2m"] if "temperature_2m" in out else 0
    pressure = out["surface_pressure"] if "surface_pressure" in out else 0
    out["mixing_height_proxy"] = pd.Series(temp).fillna(0) + pd.Series(pressure).fillna(0) / 100

    wind_speed = out["wind_speed_10m"] if "wind_speed_10m" in out else 0
    cloud_cover = out["cloud_cover"] if "cloud_cover" in out else 0
    is_day = out["is_day"] if "is_day" in out else 0
    out["atmospheric_stability_index"] = (
        (1 - pd.Series(wind_speed).fillna(0) / 20)
        + pd.Series(cloud_cover).fillna(0) / 100
        + (1 - pd.Series(is_day).fillna(0))
    ) / 3

    month = pd.to_datetime(out["timestamp"], utc=True).dt.month
    out["monsoon_season_flag"] = month.between(7, 9).astype(int)
    wind_series = out["wind_speed_10m"] if "wind_speed_10m" in out else 0
    out["winter_inversion_flag"] = (
        month.isin([12, 1, 2]) & (pd.Series(wind_series) < 5)
    ).astype(int)
    out["dust_storm_season_flag"] = month.between(4, 6).astype(int)
    out["crop_burning_season_flag"] = month.between(10, 11).astype(int)

    out["weekend_traffic_factor"] = np.where(
        pd.to_datetime(out["timestamp"], utc=True).dt.dayofweek >= 5, 0.6, 1.0
    )

    hour = pd.to_datetime(out["timestamp"], utc=True).dt.hour
    traffic_weight = np.select(
        [hour.between(7, 9), hour.between(17, 19)], [1.0, 1.0], default=0.7
    )
    traffic_weight = np.where(hour.between(0, 5), 0.3, traffic_weight)
    out["hour_traffic_weight"] = traffic_weight

    # Hours since last high wind event
    high_wind = pd.Series(wind_series) > 15
    counter = []
    hours = 0
    for flag in high_wind.fillna(False):
        if flag:
            hours = 0
        else:
            hours += 1
        counter.append(hours)
    out["pollution_accumulation_index"] = counter

    return out
