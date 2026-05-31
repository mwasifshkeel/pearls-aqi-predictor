from __future__ import annotations

import json
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

from src.data.fetch_openmeteo import fetch_air_quality, fetch_weather
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


ARTIFACTS_DIR = os.getenv("EDA_ARTIFACTS_DIR", "debug_exports")


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = add_time_features(df)
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_weather_features(df)
    df = add_pollutant_features(df)
    df = add_spatial_features(df)
    return df


def _load_top_features(default_features: list[str]) -> list[str]:
    path = os.path.join(ARTIFACTS_DIR, "top_features.json")
    if not os.path.exists(path):
        return default_features
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict) and "features" in payload:
            return [f for f in payload["features"] if f in default_features]
        if isinstance(payload, list):
            return [f for f in payload if f in default_features]
    except (OSError, json.JSONDecodeError):
        return default_features
    return default_features


def _get_fetch_window(collection) -> tuple[str, str, pd.Timestamp | None]:
    cursor = collection.find().sort("timestamp", -1).limit(1)
    latest = next(cursor, None)
    today = pd.Timestamp.utcnow().date()
    end_date = today
    if not latest or "timestamp" not in latest:
        start_date = (today - pd.Timedelta(days=365)).isoformat()
        return start_date, end_date.isoformat(), None

    latest_ts = pd.to_datetime(latest["timestamp"], utc=True, errors="coerce")
    if pd.isna(latest_ts):
        start_date = (today - pd.Timedelta(days=365)).isoformat()
        return start_date, end_date.isoformat(), None

    latest_date = min(latest_ts.date(), today)
    start_date = latest_date
    return start_date.isoformat(), end_date.isoformat(), latest_ts


def main() -> None:
    lat = float(os.getenv("RAWALPINDI_LAT", "33.6007"))
    lon = float(os.getenv("RAWALPINDI_LON", "73.0679"))

    db = get_database()
    collection = db["aqi_features_rawalpindi"]
    collection.create_index("timestamp", unique=True)

    start_date, end_date, latest_ts = _get_fetch_window(collection)
    logger.info("Fetching window start=%s end=%s latest=%s", start_date, end_date, latest_ts or "none")

    start_date_value = pd.to_datetime(start_date).date()
    if start_date_value <= pd.Timestamp.utcnow().date():
        weather = fetch_weather(
            lat,
            lon,
            start_date=start_date,
            end_date=end_date,
        )
    else:
        weather = pd.DataFrame()

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
    if latest_ts is not None:
        merged = merged[merged["timestamp"] > latest_ts]
    if merged.empty:
        logger.info("No new data found after %s", latest_ts)
        return
    logger.info("Merged forecast rows=%s", len(merged))
    features = build_features(merged)
    features = features.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    default_features = [c for c in get_feature_catalog() if c in features.columns]
    top_features = _load_top_features(default_features)
    keep_cols = ["timestamp", "european_aqi"] + top_features
    keep_cols = [c for c in keep_cols if c in features.columns]
    features = features[keep_cols]
    
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
