from sklearn.multioutput import MultiOutputRegressor
import numpy as np
import pandas as pd
import shap
import json
from typing import Any, Dict


def compute_shap_summary(model, X_sample, feature_columns):
    X_sample = X_sample.copy()

    if not isinstance(X_sample, pd.DataFrame):
        X_sample = pd.DataFrame(X_sample, columns=feature_columns)

    # -----------------------------
    # CATBOOST SPECIAL HANDLING
    # -----------------------------
    if hasattr(model, "get_feature_importance"):
        try:
            from catboost import Pool

            pool = Pool(X_sample, feature_names=list(feature_columns))
            shap_vals = model.get_feature_importance(data=pool, type="ShapValues")
            shap_vals = np.array(shap_vals)

            if shap_vals.ndim == 3:
                shap_vals = shap_vals[:, :, :-1].mean(axis=1)
            else:
                shap_vals = shap_vals[:, :-1]

            importance = np.abs(shap_vals).mean(axis=0)

            if len(importance) != len(feature_columns):
                raise RuntimeError(
                    f"SHAP importance length {len(importance)} != "
                    f"feature count {len(feature_columns)}"
                )

            idx = np.argsort(importance)[::-1]
            return {
                "features": [feature_columns[i] for i in idx],
                "importance": importance[idx].tolist(),
            }

        except Exception as e:
            raise RuntimeError(f"CatBoost SHAP failed: {e}") from e

    # -----------------------------
    # MULTIOUTPUT HANDLING
    # -----------------------------
    if isinstance(model, MultiOutputRegressor):
        # One estimator per forecast day — average SHAP importance across all of them.
        shap_values_list = []
        for est in model.estimators_:
            explainer = shap.TreeExplainer(est)
            sv = np.array(explainer.shap_values(X_sample))
            if sv.ndim == 3:
                sv = sv.mean(axis=2)
            shap_values_list.append(np.abs(sv))
        shap_values = np.mean(np.stack(shap_values_list), axis=0)

    # -----------------------------
    # STANDARD MODELS
    # -----------------------------
    else:
        explainer = shap.TreeExplainer(model)
        shap_values = np.array(explainer.shap_values(X_sample))
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