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
    metrics = {}
    horizons = y_true.shape[1]
    for idx in [23, 47, 71]:
        if idx < horizons:
            metrics[f"rmse_{idx+1}h"] = float(np.sqrt(mean_squared_error(y_true[:, idx], y_pred[:, idx])))
            metrics[f"r2_{idx+1}h"] = float(r2_score(y_true[:, idx], y_pred[:, idx]))
    return metrics
