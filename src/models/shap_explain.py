from __future__ import annotations

import json
from typing import Any, Dict

import numpy as np
import shap


def compute_shap_summary(model, X_sample, feature_names) -> Dict[str, Any]:
    base_model = model.estimators_[0] if hasattr(model, "estimators_") else model
    explainer = shap.Explainer(base_model, X_sample)
    shap_values = explainer(X_sample)

    # Flatten to 1D — handles both single and multi-output SHAP values
    mean_abs = np.abs(shap_values.values).mean(axis=0)
    if mean_abs.ndim > 1:
        mean_abs = mean_abs.mean(axis=1)  # average across output dimensions

    feature_names = list(feature_names)  # ensure plain list for scalar indexing
    top_indices = np.argsort(mean_abs)[::-1][:15].tolist()  # convert to plain ints
    top_features = [feature_names[i] for i in top_indices]
    top_values = mean_abs[top_indices].tolist()

    return {"features": top_features, "importance": top_values}

def save_shap_json(payload: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)