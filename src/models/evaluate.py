from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def evaluate_forecast(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    return {"rmse": rmse, "mae": mae, "r2": r2}


def per_horizon_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Per-day RMSE/R² for a daily-average forecast (each column = one day ahead)."""
    metrics = {}
    horizons = y_true.shape[1]
    for idx in range(horizons):
        day = idx + 1
        metrics[f"rmse_day{day}"] = float(np.sqrt(mean_squared_error(y_true[:, idx], y_pred[:, idx])))
        metrics[f"r2_day{day}"] = float(r2_score(y_true[:, idx], y_pred[:, idx]))
    return metrics
