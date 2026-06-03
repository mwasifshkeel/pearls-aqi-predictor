from __future__ import annotations

import json
from typing import Any, Dict

import numpy as np
import shap


def compute_shap_summary(model, X_sample, feature_columns):
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)
    
    # Handle multi-output: shap_values is list of (n_samples, n_features) arrays
    if isinstance(shap_values, list):
        shap_values = np.mean(np.stack(shap_values, axis=0), axis=0)  # average over horizons
    
    importance = np.abs(shap_values).mean(axis=0)
    idx = np.argsort(importance)[::-1]
    return {
        "features": [feature_columns[i] for i in idx],
        "importance": importance[idx].tolist(),
    }

def save_shap_json(payload: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)