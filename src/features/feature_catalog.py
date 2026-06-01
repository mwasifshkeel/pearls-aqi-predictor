from __future__ import annotations

from typing import List

from .lag_features import LAG_CONFIG
from .rolling_features import ROLLING_BASE_VARS, ROLLING_WINDOWS

FEATURE_SOURCES = {
    "time_features": "src/features/time_features.py",
    "lag_features": "src/features/lag_features.py",
    "rolling_features": "src/features/rolling_features.py",
    "weather_features": "src/features/weather_features.py",
    "pollutant_features": "src/features/pollutant_features.py",
    "spatial_features": "src/features/spatial_features.py",
}

TOP_FEATURES = [
    "european_aqi_lag_1h",           # corr 0.985 — was not here, critical
    "european_aqi_lag_24h",          # critical for 24h horizon
    "european_aqi_lag_48h",          # critical for 48h horizon
    "european_aqi_lag_72h",          # critical for 72h horizon
    "european_aqi_rolling_mean_3h",  # corr 0.991 — strongest rolling signal
    "european_aqi_rolling_min_3h",   # corr 0.987
    "pm2_5_rolling_mean_12h",        # corr 0.781
    "pm10_rolling_mean_24h",         # corr 0.751
    "pm10_rolling_mean_48h",         # corr 0.714
    "pm2_5_rolling_min_6h",          # corr 0.658
    "pm2_5_rolling_mean_6h",         # corr 0.658
    "european_aqi_rolling_min_168h", # corr 0.644
    "pm10_rolling_mean_12h",         # corr 0.643
    "pm2_5_rolling_mean_3h",         # corr 0.604
    "pm2_5_rolling_min_3h",          # corr 0.598
    "pm10_rolling_std_24h",          # corr 0.578
    "pm10_rolling_min_3h",           # corr 0.514
    "wind_speed_10m_rolling_std_168h", # corr 0.488
    "european_aqi_rolling_std_12h",    # corr 0.482
    "european_aqi_rolling_std_24h",    # corr 0.468
    "days_since_last_rain",            # corr 0.386
    "european_aqi_rolling_std_48h",    # corr 0.381
    "pm10_rolling_std_168h",           # corr 0.357
    "wind_speed_10m_rolling_mean_168h",
    "wind_speed_10m_rolling_mean_24h",
    "wind_speed_10m_rolling_min_168h",
    "wind_speed_10m_rolling_min_48h",
    "precipitation_cumulative_72h",    # corr 0.185
    "pollutant_composite_index",
    "oxidant_index",
    "epa_pm25_subindex",
    "epa_pm10_subindex",
    "nitrogen_dioxide_lag_6h",
    "relative_humidity_2m_rolling_min_24h",
    "relative_humidity_2m_rolling_std_24h",
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "daylight_hours",
]


def get_feature_catalog() -> List[str]:
    features = []

    time_features = [
        "hour_of_day",
        "day_of_week",
        "day_of_month",
        "month",
        "quarter",
        "is_weekend",
        "is_morning_rush",
        "is_evening_rush",
        "season",
        "hour_sin",
        "hour_cos",
        "day_of_week_sin",
        "day_of_week_cos",
        "month_sin",
        "month_cos",
        "day_of_year_sin",
        "day_of_year_cos",
        "is_pakistan_public_holiday",
        "days_since_last_rain",
    ]
    features.extend(time_features)

    for column, lags in LAG_CONFIG.items():
        for lag in lags:
            features.append(f"{column}_lag_{lag}h")

    for column in ROLLING_BASE_VARS:
        for window in ROLLING_WINDOWS:
            features.append(f"{column}_rolling_mean_{window}h")
            features.append(f"{column}_rolling_std_{window}h")
            features.append(f"{column}_rolling_min_{window}h")

    weather_features = [
        "heat_index",
        "apparent_temperature",
        "dew_point_delta",
        "pressure_change_1h",
        "pressure_change_3h",
        "pressure_change_6h",
        "wind_chill",
        "absolute_humidity",
        "vapor_pressure_deficit",
        "precipitation_cumulative_24h",
        "precipitation_cumulative_72h",
        "cloud_cover_category",
        "wind_beaufort_scale",
        "inversion_risk_flag",
        "daylight_hours",
        "solar_radiation_category",
        "uv_index_category",
        "fog_risk_index",
        "wind_gust_ratio",
        "cloud_radiation_interaction",
        "humidity_temp_interaction",
    ]
    features.extend(weather_features)

    pollutant_features = [
        "pm2_5_pm10_ratio",
        "aqi_change_rate_1h",
        "aqi_change_rate_3h",
        "aqi_change_rate_6h",
        "dominant_pollutant_pm25",
        "dominant_pollutant_pm10",
        "dominant_pollutant_no2",
        "dominant_pollutant_o3",
        "dominant_pollutant_so2",
        "epa_pm25_subindex",
        "epa_pm10_subindex",
        "epa_o3_subindex",
        "epa_no2_subindex",
        "pollutant_composite_index",
        "pm2_5_24h_average",
        "aqi_trend_slope_6h",
        "high_pm25_flag",
        "high_pm10_flag",
        "co_no2_ratio",
        "oxidant_index",
        "secondary_aerosol_proxy",
        "dust_aqi_ratio",
        "pollutant_accumulation_hours",
    ]
    features.extend(pollutant_features)

    spatial_features = [
        "wind_direction_sin",
        "wind_direction_cos",
        "wind_direction_quadrant",
        "prevailing_wind_from_industrial",
        "wind_direction_change_3h",
        "mixing_height_proxy",
        "atmospheric_stability_index",
        "monsoon_season_flag",
        "winter_inversion_flag",
        "dust_storm_season_flag",
        "crop_burning_season_flag",
        "weekend_traffic_factor",
        "hour_traffic_weight",
        "pollution_accumulation_index",
        "is_day",
    ]
    features.extend(spatial_features)

    return features
