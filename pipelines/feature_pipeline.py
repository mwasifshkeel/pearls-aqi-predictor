from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

# Ensure the project root is on sys.path for `src` imports.
_candidate_roots = [
    os.getenv("PROJECT_ROOT"),
    os.getenv("GITHUB_WORKSPACE"),
]

PROJECT_ROOT = None
for candidate in _candidate_roots:
    if candidate:
        resolved = Path(candidate).resolve()
        if (resolved / "src").is_dir():
            PROJECT_ROOT = resolved
            break

if PROJECT_ROOT is None:
    PROJECT_ROOT = next(
        (parent for parent in Path(__file__).resolve().parents if (parent / "src").is_dir()),
        None,
    )

if PROJECT_ROOT and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.fetch_openmeteo import fetch_air_quality, fetch_forecast, fetch_weather
from src.data.merge import merge_weather_aq
from src.features import (
    add_lag_features,
    add_pollutant_features,
    add_rolling_features,
    add_spatial_features,
    add_time_features,
    add_weather_features,
    get_feature_catalog,
)
from src.utils.mongo_client import get_database
from src.utils.logger import get_logger


logger = get_logger("feature_pipeline")


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = add_time_features(df)
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_weather_features(df)
    df = add_pollutant_features(df)
    df = add_spatial_features(df)
    return df


def _get_fetch_window(collection) -> tuple[str, str, str | None]:
    cursor = collection.find().sort("timestamp", -1).limit(1)
    latest = next(cursor, None)
    today = pd.Timestamp.utcnow().date()
    end_date = (today + pd.Timedelta(days=3)).isoformat()
    if not latest or "timestamp" not in latest:
        start_date = (today - pd.Timedelta(days=7)).isoformat()
        return start_date, end_date, None

    latest_ts = pd.to_datetime(latest["timestamp"], utc=True, errors="coerce")
    if pd.isna(latest_ts):
        start_date = (today - pd.Timedelta(days=7)).isoformat()
        return start_date, end_date, None

    start_date = (latest_ts - pd.Timedelta(days=1)).date().isoformat()
    return start_date, end_date, latest_ts.isoformat()


def main() -> None:
    lat = float(os.getenv("RAWALPINDI_LAT", "33.6007"))
    lon = float(os.getenv("RAWALPINDI_LON", "73.0679"))

    db = get_database()
    collection = db["aqi_features_rawalpindi"]
    collection.create_index("timestamp", unique=True)

    start_date, end_date, latest_ts = _get_fetch_window(collection)
    logger.info("Fetching window start=%s end=%s latest=%s", start_date, end_date, latest_ts or "none")

    today_date = pd.Timestamp.utcnow().date()
    start_date_value = pd.to_datetime(start_date).date()
    if start_date_value <= today_date:
        weather_archive = fetch_weather(
            lat,
            lon,
            start_date=start_date,
            end_date=today_date.isoformat(),
        )
    else:
        weather_archive = pd.DataFrame()

    weather_forecast = fetch_forecast(lat, lon, forecast_days=3, past_hours=0)
    weather = pd.concat([weather_archive, weather_forecast], ignore_index=True)
    weather = weather.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    air_quality = fetch_air_quality(lat, lon, start_date=start_date, end_date=end_date)

    logger.info(
        "Fetched forecast weather rows=%s range=%s..%s",
        len(weather),
        weather["timestamp"].min(),
        weather["timestamp"].max(),
    )
    logger.info(
        "Fetched forecast air quality rows=%s range=%s..%s",
        len(air_quality),
        air_quality["timestamp"].min(),
        air_quality["timestamp"].max(),
    )

    merged = merge_weather_aq(weather, air_quality)
    logger.info("Merged forecast rows=%s", len(merged))
    features = build_features(merged)
    features = features.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    
    # Ensure no all-null columns
    for column in features.columns:
        if features[column].isna().all():
            features[column] = 0.0

    numeric_cols = features.select_dtypes(include=["number"]).columns
    features[numeric_cols] = features[numeric_cols].astype(float).fillna(0)

    records = features.to_dict('records')
    for record in records:
        collection.update_one(
            {"timestamp": record["timestamp"]},
            {"$set": record},
            upsert=True
        )

    logger.info("Feature pipeline complete: %s rows", len(features))


if __name__ == "__main__":
    main()
