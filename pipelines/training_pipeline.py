from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import numpy as np
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

from src.features.feature_catalog import TOP_FEATURES
from src.models.evaluate import evaluate_forecast, per_horizon_metrics
from src.models.model_configs import MODEL_CONFIGS
from src.models.registry import push_model
from src.models.train import train_model
from src.models.shap_explain import compute_shap_summary, save_shap_json
from src.utils.mongo_client import get_database
from src.utils.logger import get_logger


logger = get_logger("training_pipeline")

def _coerce_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _to_native(value):
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    return value


def _store_model_metrics(db, metrics_table: List[Dict[str, float]], window_days: int, feature_count: int, updated_at: str) -> None:
    collection = db["aqi_model_metrics_rawalpindi"]
    for row in metrics_table:
        doc = {
            "model_name": row.get("model"),
            "rmse": _to_native(row.get("rmse")),
            "mae": _to_native(row.get("mae")),
            "r2": _to_native(row.get("r2")),
            "rmse_24h": _to_native(row.get("rmse_24h")),
            "rmse_48h": _to_native(row.get("rmse_48h")),
            "rmse_72h": _to_native(row.get("rmse_72h")),
            "window_days": window_days,
            "feature_count": feature_count,
            "updated_at": updated_at,
        }
        collection.update_one({"model_name": doc["model_name"]}, {"$set": doc}, upsert=True)


def _store_best_model_metadata(db, best_name: str | None, best_type: str | None, best_metrics: Dict[str, float] | None, window_days: int, feature_count: int, updated_at: str) -> None:
    if not best_name or not best_metrics:
        return
    payload = {
        "_id": "latest",
        "best_model_name": best_name,
        "best_model_type": best_type,
        "rmse": _to_native(best_metrics.get("rmse")),
        "mae": _to_native(best_metrics.get("mae")),
        "r2": _to_native(best_metrics.get("r2")),
        "rmse_24h": _to_native(best_metrics.get("rmse_24h")),
        "rmse_48h": _to_native(best_metrics.get("rmse_48h")),
        "rmse_72h": _to_native(best_metrics.get("rmse_72h")),
        "window_days": window_days,
        "feature_count": feature_count,
        "updated_at": updated_at,
    }
    db["aqi_model_metadata_rawalpindi"].update_one({"_id": "latest"}, {"$set": payload}, upsert=True)


def _store_shap_summary(db, shap_payload: Dict[str, List[float]], model_name: str, updated_at: str) -> None:
    payload = {
        "_id": "latest",
        "model_name": model_name,
        "features": shap_payload.get("features", []),
        "importance": [_to_native(value) for value in shap_payload.get("importance", [])],
        "updated_at": updated_at,
    }
    db["aqi_shap_summary_rawalpindi"].update_one({"_id": "latest"}, {"$set": payload}, upsert=True)


def _store_eda_summary(db, data: pd.DataFrame, window_days: int, updated_at: str) -> None:
    if data.empty:
        return

    aqi = data["european_aqi"].astype(float)
    median = float(aqi.median())
    p90 = float(aqi.quantile(0.9))
    max_val = float(aqi.max())

    by_hour = data.groupby(data["timestamp"].dt.hour)["european_aqi"].mean().sort_values()
    low_hours = ", ".join([f"{int(hour):02d}:00" for hour in by_hour.head(3).index])
    high_hours = ", ".join([f"{int(hour):02d}:00" for hour in by_hour.tail(3).index])

    distribution_note = (
        f"Last {window_days} days: median AQI {median:.1f}, 90th percentile {p90:.1f}, peak {max_val:.1f}."
    )
    seasonality_note = (
        f"Cleanest hours: {low_hours}. Peak AQI tends to cluster around {high_hours}."
    )

    hourly = data.copy()
    hourly["day"] = hourly["timestamp"].dt.dayofweek
    hourly["hour"] = hourly["timestamp"].dt.hour
    heatmap = hourly.groupby(["day", "hour"])["european_aqi"].mean().reset_index()

    heatmap_map = {(int(row["day"]), int(row["hour"])): float(row["european_aqi"]) for _, row in heatmap.iterrows()}
    heatmap_cells = []
    for day in range(7):
        for hour in range(24):
            heatmap_cells.append(
                {
                    "day": day,
                    "hour": hour,
                    "value": heatmap_map.get((day, hour), 0.0),
                }
            )

    payload = {
        "_id": "latest",
        "distribution_note": distribution_note,
        "seasonality_note": seasonality_note,
        "hourly_heatmap": heatmap_cells,
        "window_days": window_days,
        "updated_at": updated_at,
    }
    db["aqi_eda_summary_rawalpindi"].update_one({"_id": "latest"}, {"$set": payload}, upsert=True)


def main() -> None:
    db = get_database()
    collection = db["aqi_features_rawalpindi"]

    # Read from MongoDB and convert to pandas DF
    cursor = collection.find().sort("timestamp", 1)
    data = pd.DataFrame(list(cursor))
    if "_id" in data.columns:
        data = data.drop(columns=["_id"])

    if data.empty:
        raise ValueError("aqi_features_rawalpindi is empty")

    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
    data = data.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    only_if_new = _coerce_bool(os.getenv("TRAIN_ONLY_IF_NEW_DATA", "true"))
    if only_if_new:
        meta = db["aqi_model_metadata_rawalpindi"].find_one({"_id": "latest"})
        if meta and meta.get("updated_at"):
            last_trained = pd.to_datetime(meta.get("updated_at"), utc=True, errors="coerce")
            latest_data = data["timestamp"].max()
            if pd.notna(last_trained) and latest_data <= last_trained:
                logger.info("No new data since last training (%s); skipping.", last_trained)
                return

    top_features = list(TOP_FEATURES)
    if not top_features:
        raise ValueError("No top features configured")
    feature_columns = [feature for feature in top_features if feature in data.columns]
    if not feature_columns:
        raise ValueError("No top features available in dataset")
    daily_model_names = {"catboost", "gradient_boosting", "extra_trees", "random_forest"}
    model_configs = [config for config in MODEL_CONFIGS if config.name in daily_model_names]
    if not model_configs:
        raise ValueError("No matching model configs found for daily training list")

    cutoff_days = 90  # Best window from EDA time-window study.
    logger.info("Training window days=%s (source=eda)", cutoff_days)

    cutoff_time = data["timestamp"].max() - pd.Timedelta(days=cutoff_days)
    data = data[data["timestamp"] >= cutoff_time]

    if not feature_columns:
        raise ValueError("No feature columns available for training")

    target = data["european_aqi"].astype(float)
    X = data[feature_columns].astype(float).ffill().fillna(0)

    horizon = 72
    if len(target) <= horizon:
        logger.warning("Not enough data to train: rows=%s horizon=%s", len(target), horizon)
        return

    X_model = X.iloc[:-horizon]
    y_model = pd.DataFrame(
        [target.iloc[i : i + horizon].values for i in range(len(target) - horizon)]
    )

    metrics_table = []
    best_model = None
    best_metrics = None
    best_name = None
    best_type = None

    for config in model_configs:
        model, preds, y_true = train_model(config, X_model, y_model, horizon=horizon)
        metrics = evaluate_forecast(y_true, preds)
        metrics.update(per_horizon_metrics(y_true, preds))
        metrics_table.append({"model": config.name, **metrics})

        if best_metrics is None or metrics["rmse"] < best_metrics["rmse"]:
            best_metrics = metrics
            best_model = model
            best_name = config.name
            best_type = config.type

    metrics_df = pd.DataFrame(metrics_table).sort_values("rmse")
    logger.info("Model ranking:\n%s", metrics_df.to_string(index=False))

    artifacts_dir = "/tmp/aqi_model"
    os.makedirs(artifacts_dir, exist_ok=True)
    metrics_path = os.path.join(artifacts_dir, "metrics.csv")
    metrics_df.to_csv(metrics_path, index=False)

    updated_at = datetime.now(timezone.utc).isoformat()
    _store_model_metrics(db, metrics_table, cutoff_days, len(feature_columns), updated_at)
    _store_best_model_metadata(db, best_name, best_type, best_metrics, cutoff_days, len(feature_columns), updated_at)

    pred_df = None
    if best_model is not None and best_name:
        latest_features = X.tail(horizon)
        if best_type in {"gru", "lstm"}:
            lookback = 24
            if len(X) < lookback:
                return
            seq = X.tail(lookback).values.reshape(1, lookback, X.shape[1])
            preds = best_model.predict(seq)
        else:
            preds = best_model.predict(latest_features.iloc[:1])

        predictions = preds.flatten()
        pred_times = data["timestamp"].tail(horizon).values
        pred_df = pd.DataFrame(
            {
                "timestamp": pred_times,
                "predicted_aqi": predictions[:horizon],
                "model_name": best_name,
                "horizon_hours": list(range(1, horizon + 1)),
                "confidence_lower": predictions[:horizon] * 0.9,
                "confidence_upper": predictions[:horizon] * 1.1,
            }
        )

        predictions_path = os.path.join(artifacts_dir, "predictions.csv")
        pred_df.to_csv(predictions_path, index=False)

        pred_collection = db["aqi_predictions_rawalpindi"]
        pred_collection.create_index([("timestamp", 1), ("model_name", 1)], unique=True)

        records = pred_df.to_dict("records")
        for record in records:
            pred_collection.update_one(
                {"timestamp": record["timestamp"], "model_name": record["model_name"]},
                {"$set": record},
                upsert=True,
            )

    if best_model is not None and best_type in {"lgbm", "xgb", "cat", "rf", "extra", "gbr"}:
        shap_payload = compute_shap_summary(best_model, X_model.sample(200), feature_columns)
        shap_path = os.path.join(artifacts_dir, "shap_summary.json")
        save_shap_json(shap_payload, shap_path)

        model_metadata = {
            "model_type": best_type,
            "window_days": cutoff_days,
            "feature_count": len(feature_columns),
            "horizon_hours": horizon,
        }

        push_model(
            best_model,
            name=f"{best_name}_aqi_rawalpindi",
            metrics=best_metrics,
            artifacts_path=artifacts_dir,
            metadata=model_metadata,
        )
        _store_shap_summary(db, shap_payload, best_name, updated_at)

    _store_eda_summary(db, data, cutoff_days, updated_at)


if __name__ == "__main__":
    main()
