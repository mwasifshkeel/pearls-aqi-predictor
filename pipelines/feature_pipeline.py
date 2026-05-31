from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

# Ensure the project root is on sys.path for `src` imports.
PROJECT_ROOT = next(
    (parent for parent in Path(__file__).resolve().parents if (parent / "src").is_dir()),
    None,
)
if PROJECT_ROOT and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.fetch_openmeteo import fetch_air_quality, fetch_forecast
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


def main() -> None:
    lat = float(os.getenv("RAWALPINDI_LAT", "33.6007"))
    lon = float(os.getenv("RAWALPINDI_LON", "73.0679"))

    weather = fetch_forecast(lat, lon, past_hours=168)
    air_quality = fetch_air_quality(lat, lon, past_days=7)

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
    
    # Ensure no all-null columns
    for column in features.columns:
        if features[column].isna().all():
            features[column] = 0.0

    numeric_cols = features.select_dtypes(include=["number"]).columns
    features[numeric_cols] = features[numeric_cols].astype(float).fillna(0)

    db = get_database()
    collection = db["aqi_features_rawalpindi"]
    collection.create_index("timestamp", unique=True)
    
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
