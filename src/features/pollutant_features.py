from __future__ import annotations

import numpy as np
import pandas as pd


def _aqi_subindex(value: pd.Series, breakpoints):
    index = pd.Series(np.nan, index=value.index)
    for (c_low, c_high, i_low, i_high) in breakpoints:
        mask = (value >= c_low) & (value <= c_high)
        index[mask] = (i_high - i_low) / (c_high - c_low) * (value[mask] - c_low) + i_low
    return index


PM25_BREAKPOINTS = [
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
]

PM10_BREAKPOINTS = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 504, 301, 400),
    (505, 604, 401, 500),
]

O3_BREAKPOINTS = [
    (0.000, 0.054, 0, 50),
    (0.055, 0.070, 51, 100),
    (0.071, 0.085, 101, 150),
    (0.086, 0.105, 151, 200),
    (0.106, 0.200, 201, 300),
]

NO2_BREAKPOINTS = [
    (0.000, 0.053, 0, 50),
    (0.054, 0.100, 51, 100),
    (0.101, 0.360, 101, 150),
    (0.361, 0.649, 151, 200),
    (0.650, 1.249, 201, 300),
    (1.250, 2.049, 301, 400),
    (2.050, 3.049, 401, 500),
]


def add_pollutant_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["pm2_5_pm10_ratio"] = out.get("pm2_5") / out.get("pm10")

    for hours in [1, 3, 6]:
        out[f"aqi_change_rate_{hours}h"] = (
            out.get("european_aqi").diff(hours) / hours
        )

    pm25_sub = _aqi_subindex(out.get("pm2_5"), PM25_BREAKPOINTS)
    pm10_sub = _aqi_subindex(out.get("pm10"), PM10_BREAKPOINTS)

    # O3/NO2 are assumed in ppm after conversion from ug/m3 if present
    o3_sub = _aqi_subindex(out.get("ozone") / 1000, O3_BREAKPOINTS)
    no2_sub = _aqi_subindex(out.get("nitrogen_dioxide") / 1000, NO2_BREAKPOINTS)

    out["epa_pm25_subindex"] = pm25_sub
    out["epa_pm10_subindex"] = pm10_sub
    out["epa_o3_subindex"] = o3_sub
    out["epa_no2_subindex"] = no2_sub

    sub_df = pd.DataFrame(
        {
            "pm25": pm25_sub,
            "pm10": pm10_sub,
            "no2": no2_sub,
            "o3": o3_sub,
            "so2": out.get("sulphur_dioxide"),
        }
    )

    dominant = sub_df.idxmax(axis=1)
    out["dominant_pollutant_pm25"] = (dominant == "pm25").astype(int)
    out["dominant_pollutant_pm10"] = (dominant == "pm10").astype(int)
    out["dominant_pollutant_no2"] = (dominant == "no2").astype(int)
    out["dominant_pollutant_o3"] = (dominant == "o3").astype(int)
    out["dominant_pollutant_so2"] = (dominant == "so2").astype(int)

    out["pollutant_composite_index"] = (
        pm25_sub.fillna(0) * 0.35
        + pm10_sub.fillna(0) * 0.2
        + no2_sub.fillna(0) * 0.15
        + o3_sub.fillna(0) * 0.2
        + out.get("sulphur_dioxide").fillna(0) * 0.1
    )

    out["pm2_5_24h_average"] = out.get("pm2_5").rolling(window=24, min_periods=1).mean()

    out["aqi_trend_slope_6h"] = (
        out.get("european_aqi").rolling(window=6, min_periods=2).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=False
        )
    )

    out["high_pm25_flag"] = (out.get("pm2_5") > 35.4).astype(int)
    out["high_pm10_flag"] = (out.get("pm10") > 154).astype(int)

    out["co_no2_ratio"] = out.get("carbon_monoxide") / out.get("nitrogen_dioxide")
    out["oxidant_index"] = out.get("ozone") + out.get("nitrogen_dioxide")
    out["secondary_aerosol_proxy"] = out.get("sulphur_dioxide") + out.get("nitrogen_dioxide")
    out["dust_aqi_ratio"] = out.get("dust") / out.get("european_aqi")

    # Consecutive hours with AQI > 100
    threshold = out.get("european_aqi") > 100
    accumulation = []
    count = 0
    for flag in threshold.fillna(False):
        if flag:
            count += 1
        else:
            count = 0
        accumulation.append(count)
    out["pollutant_accumulation_hours"] = accumulation

    return out
