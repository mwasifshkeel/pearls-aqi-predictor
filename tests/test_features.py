import pandas as pd

from src.features import (
    add_lag_features,
    add_pollutant_features,
    add_rolling_features,
    add_spatial_features,
    add_time_features,
    add_weather_features,
)


def test_feature_generation_columns():
    ts = pd.date_range("2025-01-01", periods=10, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "timestamp": ts,
            "temperature_2m": 20,
            "relative_humidity_2m": 50,
            "dew_point_2m": 10,
            "precipitation": 0,
            "surface_pressure": 1010,
            "wind_speed_10m": 5,
            "wind_direction_10m": 90,
            "wind_gusts_10m": 7,
            "cloud_cover": 40,
            "visibility": 8000,
            "sunshine_duration": 3600,
            "shortwave_radiation": 200,
            "uv_index": 3,
            "pm2_5": 20,
            "pm10": 40,
            "nitrogen_dioxide": 30,
            "carbon_monoxide": 0.5,
            "sulphur_dioxide": 10,
            "ozone": 50,
            "dust": 20,
            "european_aqi": 80,
            "is_day": 1,
        }
    )

    df = add_time_features(df)
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_weather_features(df)
    df = add_pollutant_features(df)
    df = add_spatial_features(df)

    assert "hour_sin" in df.columns
    assert "pm2_5_lag_1h" in df.columns
    assert "pm10_rolling_mean_24h" in df.columns
    assert "heat_index" in df.columns
    assert "pm2_5_pm10_ratio" in df.columns
    assert "wind_direction_sin" in df.columns
