from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pandas as pd
import numpy as np

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
from src.features.feature_catalog import TOP_FEATURES
from src.utils.mongo_client import get_database
from src.utils.logger import get_logger


logger = get_logger("feature_pipeline")


ROLLING_RE = re.compile(r"(.+)_rolling_(mean|std|min)_(\d+)h$")
LAG_RE = re.compile(r"(.+)_lag_(\d+)h$")


def _series_or_nan(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame:
        return frame[column]
    return pd.Series(np.nan, index=frame.index)


def _parse_rolling_features(features: set[str]) -> dict[str, dict[int, set[str]]]:
    spec: dict[str, dict[int, set[str]]] = {}
    for feature in features:
        match = ROLLING_RE.match(feature)
        if not match:
            continue
        base, stat, window = match.groups()
        window_int = int(window)
        spec.setdefault(base, {}).setdefault(window_int, set()).add(stat)
    return spec


def _parse_lag_features(features: set[str]) -> dict[str, set[int]]:
    spec: dict[str, set[int]] = {}
    for feature in features:
        match = LAG_RE.match(feature)
        if not match:
            continue
        base, lag = match.groups()
        spec.setdefault(base, set()).add(int(lag))
    return spec


def build_features(df: pd.DataFrame, selected_features: list[str]) -> pd.DataFrame:
    selected = set(selected_features)
    rolling_spec = _parse_rolling_features(selected)
    lag_spec = _parse_lag_features(selected)

    base_cols = {"timestamp", "european_aqi"}
    base_cols.update(rolling_spec.keys())
    base_cols.update(lag_spec.keys())

    if "solar_radiation_category" in selected or "is_day" in selected:
        base_cols.add("shortwave_radiation")
    if "precipitation_cumulative_72h" in selected or "days_since_last_rain" in selected:
        base_cols.add("precipitation")
    if "pressure_change_6h" in selected:
        base_cols.add("surface_pressure")
    if "oxidant_index" in selected:
        base_cols.update({"ozone", "nitrogen_dioxide"})
    if "is_day" in selected:
        base_cols.add("is_day")

    available_cols = [col for col in base_cols if col in df.columns]
    out = df[available_cols].copy()
    ts = pd.to_datetime(out["timestamp"], utc=True)

    need_hour = any(
        feature in selected
        for feature in ["hour_of_day", "hour_sin", "hour_cos", "is_evening_rush", "hour_traffic_weight"]
    )
    need_day_of_week = any(
        feature in selected
        for feature in ["day_of_week", "day_of_week_sin", "day_of_week_cos", "weekend_traffic_factor"]
    )

    hour = ts.dt.hour if need_hour else None
    day_of_week = ts.dt.dayofweek if need_day_of_week else None

    if "hour_of_day" in selected:
        out["hour_of_day"] = hour
    if "day_of_week" in selected:
        out["day_of_week"] = day_of_week
    if "hour_sin" in selected:
        out["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    if "hour_cos" in selected:
        out["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    if "day_of_week_sin" in selected:
        out["day_of_week_sin"] = np.sin(2 * np.pi * day_of_week / 7)
    if "day_of_week_cos" in selected:
        out["day_of_week_cos"] = np.cos(2 * np.pi * day_of_week / 7)
    if "is_evening_rush" in selected:
        out["is_evening_rush"] = hour.between(17, 19).astype(int)

    if "days_since_last_rain" in selected:
        if "precipitation" in out:
            precip = out["precipitation"].fillna(0)
            days_since = []
            last_rain = None
            for idx, value in enumerate(precip):
                if value > 0:
                    last_rain = idx
                    days_since.append(0)
                else:
                    if last_rain is None:
                        days_since.append(np.nan)
                    else:
                        hours_since = idx - last_rain
                        days_since.append(hours_since / 24)
            out["days_since_last_rain"] = days_since
        else:
            out["days_since_last_rain"] = np.nan

    for base, windows in rolling_spec.items():
        if base in out:
            for window, stats in windows.items():
                rolling = out[base].rolling(window=window, min_periods=1)
                if "mean" in stats:
                    out[f"{base}_rolling_mean_{window}h"] = rolling.mean()
                if "std" in stats:
                    out[f"{base}_rolling_std_{window}h"] = rolling.std()
                if "min" in stats:
                    out[f"{base}_rolling_min_{window}h"] = rolling.min()
        else:
            for window, stats in windows.items():
                for stat in stats:
                    out[f"{base}_rolling_{stat}_{window}h"] = np.nan

    for base, lags in lag_spec.items():
        if base in out:
            for lag in lags:
                out[f"{base}_lag_{lag}h"] = out[base].shift(lag)
        else:
            for lag in lags:
                out[f"{base}_lag_{lag}h"] = np.nan

    if "pressure_change_6h" in selected:
        if "surface_pressure" in out:
            out["pressure_change_6h"] = out["surface_pressure"].diff(6)
        else:
            out["pressure_change_6h"] = np.nan

    if "precipitation_cumulative_72h" in selected:
        if "precipitation" in out:
            out["precipitation_cumulative_72h"] = out["precipitation"].rolling(window=72, min_periods=1).sum()
        else:
            out["precipitation_cumulative_72h"] = np.nan

    if "solar_radiation_category" in selected:
        if "shortwave_radiation" in out:
            out["solar_radiation_category"] = pd.cut(
                out["shortwave_radiation"],
                bins=[-1, 100, 300, 600, 2000],
                labels=[0, 1, 2, 3],
            ).astype(float)
        else:
            out["solar_radiation_category"] = np.nan

    if "oxidant_index" in selected:
        out["oxidant_index"] = _series_or_nan(out, "ozone") + _series_or_nan(out, "nitrogen_dioxide")

    if "weekend_traffic_factor" in selected:
        out["weekend_traffic_factor"] = np.where(day_of_week >= 5, 0.6, 1.0)

    if "hour_traffic_weight" in selected:
        traffic_weight = np.select(
            [hour.between(7, 9), hour.between(17, 19)], [1.0, 1.0], default=0.7
        )
        traffic_weight = np.where(hour.between(0, 5), 0.3, traffic_weight)
        out["hour_traffic_weight"] = traffic_weight

    if "is_day" in selected:
        if "is_day" not in out:
            if "shortwave_radiation" in out:
                out["is_day"] = out["shortwave_radiation"].fillna(0).gt(0).astype(int)
            else:
                out["is_day"] = ts.dt.hour.between(6, 18).astype(int)
        else:
            if out["is_day"].isna().any():
                fallback = ts.dt.hour.between(6, 18).astype(int)
                out["is_day"] = out["is_day"].fillna(fallback)

    return out


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
    collection_name = "aqi_features_live_rawalpindi"
    collection = db[collection_name]
    collection.create_index("timestamp", unique=True)

    start_date, end_date, latest_ts = _get_fetch_window(collection)
    logger.info("Fetching window start=%s end=%s latest=%s", start_date, end_date, latest_ts or "none")
    cutoff_ts = pd.Timestamp.utcnow().floor("H")
    logger.info("Applying fetch cutoff at %s", cutoff_ts)

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
    if not weather.empty:
        weather = weather[weather["timestamp"] <= cutoff_ts]

    air_quality = fetch_air_quality(lat, lon, start_date=start_date, end_date=end_date)
    if not air_quality.empty:
        air_quality = air_quality[air_quality["timestamp"] <= cutoff_ts]

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
    if not merged.empty:
        merged = merged[merged["timestamp"] <= cutoff_ts]
    if latest_ts is not None and latest_ts >= cutoff_ts:
        logger.info("Latest timestamp %s is beyond cutoff; refreshing current-day data", latest_ts)
        latest_ts = None
    if latest_ts is not None:
        merged = merged[merged["timestamp"] > latest_ts]
    if merged.empty:
        logger.info("No new data found after %s", latest_ts)
        return
    logger.info("Merged forecast rows=%s", len(merged))

    top_features = list(TOP_FEATURES)
    if not top_features:
        raise ValueError("No top features configured")
    features = build_features(merged, top_features)
    features = features.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    ui_columns = ["pm2_5", "pm10", "wind_speed_10m", "relative_humidity_2m"]
    ui_columns = [column for column in ui_columns if column in merged.columns]
    if ui_columns:
        features = features.merge(merged[["timestamp", *ui_columns]], on="timestamp", how="left")

    keep_cols = ["timestamp", "european_aqi"] + top_features + ui_columns
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
