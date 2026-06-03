from sklearn.multioutput import MultiOutputRegressor
import numpy as np
import pandas as pd
import shap
import json
from typing import Any, Dict

def compute_shap_summary(model, X_sample, feature_columns):

    X_sample = X_sample.copy()

    # Ensure DataFrame consistency
    if not isinstance(X_sample, pd.DataFrame):
        X_sample = pd.DataFrame(X_sample, columns=feature_columns)

    # -----------------------------
    # CATBOOST SPECIAL HANDLING
    # -----------------------------
    if hasattr(model, "get_feature_importance"):
        try:
            shap_vals = model.get_feature_importance(
                data=X_sample,
                type="ShapValues"
            )

            # last column is expected value → remove it
            shap_vals = np.array(shap_vals)[:, :-1]

            importance = np.abs(shap_vals).mean(axis=0)

            idx = np.argsort(importance)[::-1]

            return {
                "features": [feature_columns[i] for i in idx],
                "importance": importance[idx].tolist(),
            }

        except Exception as e:
            raise RuntimeError(f"CatBoost SHAP failed: {e}")

    # -----------------------------
    # MULTIOUTPUT HANDLING
    # -----------------------------
    if isinstance(model, MultiOutputRegressor):
        shap_values_list = []

        for est in model.estimators_[:5]:
            explainer = shap.TreeExplainer(est)
            sv = explainer.shap_values(X_sample)

            sv = np.array(sv)
            if sv.ndim == 3:
                sv = sv.mean(axis=2)

            shap_values_list.append(np.abs(sv))

        shap_values = np.mean(np.stack(shap_values_list), axis=0)

    # -----------------------------
    # STANDARD MODELS
    # -----------------------------
    else:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sample)

        shap_values = np.array(shap_values)

        if shap_values.ndim == 3:
            shap_values = shap_values.mean(axis=2)

        shap_values = np.abs(shap_values)

    importance = shap_values.mean(axis=0)
    idx = np.argsort(importance)[::-1]

    return {
        "features": [feature_columns[i] for i in idx],
        "importance": importance[idx].tolist(),
    }

def save_shap_json(payload: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)