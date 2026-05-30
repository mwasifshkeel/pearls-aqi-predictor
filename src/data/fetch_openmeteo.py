from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional

import pandas as pd
import requests


WEATHER_HOURLY = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "snowfall",
    "snow_depth",
    "weather_code",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "visibility",
    "wind_speed_10m",
    "wind_speed_80m",
    "wind_direction_10m",
    "wind_direction_80m",
    "wind_gusts_10m",
    "surface_pressure",
    "vapour_pressure_deficit",
    "et0_fao_evapotranspiration",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "sunshine_duration",
    "uv_index",
    "uv_index_clear_sky",
    "is_day",
    "terrestrial_radiation",
]

AIR_QUALITY_HOURLY = [
    "pm10",
    "pm2_5",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "aerosol_optical_depth",
    "dust",
    "uv_index",
    "uv_index_clear_sky",
    "ammonia",
    "alder_pollen",
    "birch_pollen",
    "grass_pollen",
    "mugwort_pollen",
    "olive_pollen",
    "ragweed_pollen",
    "european_aqi",
    "european_aqi_pm2_5",
    "european_aqi_pm10",
    "european_aqi_nitrogen_dioxide",
    "european_aqi_ozone",
    "european_aqi_sulphur_dioxide",
]


def _request(url: str, params: Dict[str, str]) -> Dict:
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def _parse_hourly(payload: Dict) -> pd.DataFrame:
    hourly = payload.get("hourly", {})
    time = hourly.get("time", [])
    df = pd.DataFrame(hourly)
    if "time" in df:
        df["timestamp"] = pd.to_datetime(df["time"], utc=True)
        df = df.drop(columns=["time"])
    else:
        df["timestamp"] = pd.to_datetime(time, utc=True)
    return df


def fetch_weather(
    lat: float,
    lon: float,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timezone: str = "Asia/Karachi",
) -> pd.DataFrame:
    url = "https://archive-api.open-meteo.com/v1/archive"
    if not start_date or not end_date:
        today = dt.date.today()
        start_date = (today - dt.timedelta(days=92)).isoformat()
        end_date = today.isoformat()
    params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(WEATHER_HOURLY),
        "timezone": timezone,
    }
    payload = _request(url, params)
    return _parse_hourly(payload)


def fetch_air_quality(
    lat: float,
    lon: float,
    past_days: int = 92,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timezone: str = "Asia/Karachi",
) -> pd.DataFrame:
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "hourly": ",".join(AIR_QUALITY_HOURLY),
        "timezone": timezone,
    }
    if start_date and end_date:
        params["start_date"] = start_date
        params["end_date"] = end_date
    else:
        params["past_days"] = str(past_days)
        params["forecast_days"] = "3"
    payload = _request(url, params)
    return _parse_hourly(payload)


def fetch_forecast(
    lat: float,
    lon: float,
    forecast_days: int = 3,
    timezone: str = "Asia/Karachi",
    past_hours: int = 72,
) -> pd.DataFrame:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "hourly": ",".join(WEATHER_HOURLY),
        "forecast_days": str(forecast_days),
        "past_hours": str(past_hours),
        "timezone": timezone,
    }
    payload = _request(url, params)
    return _parse_hourly(payload)
