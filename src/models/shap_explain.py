from sklearn.multioutput import MultiOutputRegressor
import numpy as np
import shap
import json
from typing import Any, Dict


def compute_shap_summary(model, X_sample, feature_columns):

    # unwrap MultiOutputRegressor safely
    if isinstance(model, MultiOutputRegressor):
        estimators = model.estimators_
        shap_values_list = []

        for est in estimators[:5]:  # sample a few horizons (faster + stable)
            explainer = shap.TreeExplainer(est)
            sv = explainer.shap_values(X_sample)

            if isinstance(sv, list):
                sv = np.mean(np.stack(sv), axis=0)

            if sv.ndim == 3:
                sv = np.mean(sv, axis=2)

            shap_values_list.append(np.abs(sv))

        shap_values = np.mean(np.stack(shap_values_list), axis=0)

    else:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sample)

        if isinstance(shap_values, list):
            shap_values = np.mean(np.stack(shap_values), axis=0)

        if shap_values.ndim == 3:
            shap_values = np.mean(shap_values, axis=2)

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