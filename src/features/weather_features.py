from __future__ import annotations

import numpy as np
import pandas as pd


def _heat_index(temp_c: pd.Series, rh: pd.Series) -> pd.Series:
    temp_f = temp_c * 9 / 5 + 32
    hi_f = (
        -42.379
        + 2.04901523 * temp_f
        + 10.14333127 * rh
        - 0.22475541 * temp_f * rh
        - 0.00683783 * temp_f**2
        - 0.05481717 * rh**2
        + 0.00122874 * temp_f**2 * rh
        + 0.00085282 * temp_f * rh**2
        - 0.00000199 * temp_f**2 * rh**2
    )
    return (hi_f - 32) * 5 / 9


def _wind_chill(temp_c: pd.Series, wind_kph: pd.Series) -> pd.Series:
    v = wind_kph
    return 13.12 + 0.6215 * temp_c - 11.37 * v**0.16 + 0.3965 * temp_c * v**0.16


def _absolute_humidity(temp_c: pd.Series, rh: pd.Series) -> pd.Series:
    # Approximation based on temperature and relative humidity
    temp_k = temp_c + 273.15
    sat_vapor = 6.112 * np.exp((17.67 * temp_c) / (temp_c + 243.5))
    vapor_pressure = rh / 100 * sat_vapor
    return 2.1674 * vapor_pressure / temp_k * 1000


def add_weather_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    temp = out["temperature_2m"] if "temperature_2m" in out else None
    rh = out["relative_humidity_2m"] if "relative_humidity_2m" in out else None

    if temp is not None and rh is not None:
        out["heat_index"] = _heat_index(temp, rh)
        out["dew_point_delta"] = temp - out.get("dew_point_2m")
        out["absolute_humidity"] = _absolute_humidity(temp, rh)
        out["humidity_temp_interaction"] = rh * temp
    else:
        out["heat_index"] = np.nan
        out["dew_point_delta"] = np.nan
        out["absolute_humidity"] = np.nan
        out["humidity_temp_interaction"] = np.nan

    if "surface_pressure" in out:
        out["pressure_change_1h"] = out["surface_pressure"].diff(1)
        out["pressure_change_3h"] = out["surface_pressure"].diff(3)
        out["pressure_change_6h"] = out["surface_pressure"].diff(6)
    else:
        out["pressure_change_1h"] = np.nan
        out["pressure_change_3h"] = np.nan
        out["pressure_change_6h"] = np.nan

    wind_speed = out["wind_speed_10m"] if "wind_speed_10m" in out else None
    if wind_speed is not None and temp is not None:
        out["wind_chill"] = _wind_chill(temp, wind_speed)
        out["wind_beaufort_scale"] = pd.cut(
            wind_speed,
            bins=[-1, 1, 6, 12, 20, 29, 39, 50, 62, 75, 89, 103, 118, 1000],
            labels=list(range(13)),
        ).astype(float)
    else:
        out["wind_chill"] = np.nan
        out["wind_beaufort_scale"] = np.nan

    out["vapor_pressure_deficit"] = (
        out["vapour_pressure_deficit"] if "vapour_pressure_deficit" in out else np.nan
    )

    if "precipitation" in out:
        out["precipitation_cumulative_24h"] = (
            out["precipitation"].rolling(window=24, min_periods=1).sum()
        )
        out["precipitation_cumulative_72h"] = (
            out["precipitation"].rolling(window=72, min_periods=1).sum()
        )
    else:
        out["precipitation_cumulative_24h"] = np.nan
        out["precipitation_cumulative_72h"] = np.nan

    cloud_cover = out["cloud_cover"] if "cloud_cover" in out else None
    if cloud_cover is not None:
        out["cloud_cover_category"] = pd.cut(
            cloud_cover,
            bins=[-1, 20, 80, 101],
            labels=[0, 1, 2],
        ).astype(float)
    else:
        out["cloud_cover_category"] = np.nan

    if "wind_speed_10m" in out and "relative_humidity_2m" in out:
        out["inversion_risk_flag"] = (
            (out["wind_speed_10m"] < 5) & (out["relative_humidity_2m"] > 80)
        ).astype(int)
    else:
        out["inversion_risk_flag"] = np.nan

    if "sunshine_duration" in out:
        out["daylight_hours"] = (
            out["sunshine_duration"].rolling(window=24, min_periods=1).sum() / 3600
        )
    else:
        out["daylight_hours"] = np.nan

    shortwave = out["shortwave_radiation"] if "shortwave_radiation" in out else None
    if shortwave is not None:
        out["solar_radiation_category"] = pd.cut(
            shortwave,
            bins=[-1, 100, 300, 600, 2000],
            labels=[0, 1, 2, 3],
        ).astype(float)
    else:
        out["solar_radiation_category"] = np.nan

    uv = out["uv_index"] if "uv_index" in out else None
    if uv is not None:
        out["uv_index_category"] = pd.cut(
            uv,
            bins=[-1, 2, 5, 7, 10, 20],
            labels=[0, 1, 2, 3, 4],
        ).astype(float)
    else:
        out["uv_index_category"] = np.nan

    rh_safe = out["relative_humidity_2m"] if "relative_humidity_2m" in out else 0
    visibility_safe = out["visibility"] if "visibility" in out else 0
    wind_safe = out["wind_speed_10m"] if "wind_speed_10m" in out else 0
    out["fog_risk_index"] = (
        pd.Series(rh_safe).fillna(0) / 100
        + (1 - pd.Series(visibility_safe).fillna(0) / 10000)
        + (1 - pd.Series(wind_safe).fillna(0) / 20)
    ) / 3

    if "wind_gusts_10m" in out and "wind_speed_10m" in out:
        out["wind_gust_ratio"] = out["wind_gusts_10m"] / out["wind_speed_10m"]
    else:
        out["wind_gust_ratio"] = np.nan

    if "cloud_cover" in out and "shortwave_radiation" in out:
        out["cloud_radiation_interaction"] = (
            out["cloud_cover"].fillna(0) * out["shortwave_radiation"].fillna(0)
        )
    else:
        out["cloud_radiation_interaction"] = np.nan

    return out
