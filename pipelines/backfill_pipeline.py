from __future__ import annotations

import os
import sys
import datetime as dt
from pathlib import Path

# Ensure repo root is on sys.path when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.fetch_openmeteo import fetch_air_quality, fetch_weather
from src.data.merge import merge_weather_aq
from src.features import (
    add_lag_features,
    add_pollutant_features,
    add_rolling_features,
    add_spatial_features,
    add_time_features,
    add_weather_features,
)
from src.utils.mongo_client import get_database
from src.utils.logger import get_logger


logger = get_logger("backfill_pipeline")


def main() -> None:
    lat = float(os.getenv("RAWALPINDI_LAT", "33.6007"))
    lon = float(os.getenv("RAWALPINDI_LON", "73.0679"))
    today = dt.date.today()
    start_date = os.getenv("BACKFILL_START_DATE", (today - dt.timedelta(days=365)).isoformat())
    end_date = os.getenv("BACKFILL_END_DATE", today.isoformat())

    start_value = dt.date.fromisoformat(start_date)
    end_value = dt.date.fromisoformat(end_date)
    if end_value > today:
        end_value = today
        end_date = end_value.isoformat()
    if start_value > end_value:
        start_value = end_value - dt.timedelta(days=365)
        start_date = start_value.isoformat()

    weather = fetch_weather(lat, lon, start_date=start_date, end_date=end_date)
    air_quality = fetch_air_quality(lat, lon, start_date=start_date, end_date=end_date)

    logger.info(
        "Fetched weather rows=%s range=%s..%s",
        len(weather),
        weather["timestamp"].min(),
        weather["timestamp"].max(),
    )
    logger.info(
        "Fetched air quality rows=%s range=%s..%s",
        len(air_quality),
        air_quality["timestamp"].min(),
        air_quality["timestamp"].max(),
    )

    merged = merge_weather_aq(weather, air_quality)
    logger.info(
        "Merged rows=%s missing_timestamp=%s",
        len(merged),
        int(merged["timestamp"].isna().sum()),
    )
    df = add_time_features(merged)
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_weather_features(df)
    df = add_pollutant_features(df)
    df = add_spatial_features(df)

    # Ensure no all-null columns cause unsupported dtypes in storage
    for column in df.columns:
        if df[column].isna().all():
            df[column] = 0.0

    numeric_cols = df.select_dtypes(include=["number"]).columns
    df[numeric_cols] = df[numeric_cols].astype(float).fillna(0)
    
    db = get_database()
    collection = db["aqi_features_rawalpindi"]
    
    # Create unique index on timestamp
    collection.create_index("timestamp", unique=True)

    # Clean up future rows and (optionally) data older than the backfill window.
    cutoff_end = dt.datetime.combine(end_value, dt.time.max, tzinfo=dt.timezone.utc)
    cutoff_start = dt.datetime.combine(start_value, dt.time.min, tzinfo=dt.timezone.utc)
    delete_future = collection.delete_many({"timestamp": {"$gt": cutoff_end}})
    logger.info("Deleted future rows: %s", delete_future.deleted_count)

    clean_old = os.getenv("CLEAN_OLD_DATA", "true").strip().lower() in {"1", "true", "yes", "y"}
    if clean_old:
        delete_old = collection.delete_many({"timestamp": {"$lt": cutoff_start}})
        logger.info("Deleted old rows before %s: %s", cutoff_start.isoformat(), delete_old.deleted_count)
    
    # Upsert records using batched bulk_write for performance
    from pymongo import UpdateOne

    records = df.to_dict("records")
    total = len(records)
    batch_size = int(os.getenv("BULK_BATCH_SIZE", "1000"))
    logger.info("Bulk upsert %s records to %s with batch_size=%s", total, collection.name, batch_size)

    ops = []
    for i, record in enumerate(records, start=1):
        ops.append(UpdateOne({"timestamp": record["timestamp"]}, {"$set": record}, upsert=True))
        if len(ops) >= batch_size or i == total:
            try:
                result = collection.bulk_write(ops, ordered=False)
                logger.info("Bulk write batch complete: ops=%s inserted=%s modified=%s", len(ops), getattr(result, 'upserted_count', 'N/A'), getattr(result, 'modified_count', 'N/A'))
            except Exception:
                logger.exception("Bulk write failed for batch ending at index %s", i)
            ops = []

    logger.info("Backfill complete: attempted upsert of %s rows", total)


if __name__ == "__main__":
    main()
