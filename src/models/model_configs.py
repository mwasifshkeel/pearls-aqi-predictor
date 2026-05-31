from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ModelConfig:
    name: str
    type: str
    params: Dict


MODEL_CONFIGS: List[ModelConfig] = [
    ModelConfig(
        name="lightgbm",
        type="lgbm",
        params={"n_estimators": 300, "learning_rate": 0.05, "num_leaves": 31},
    ),
    ModelConfig(
        name="xgboost",
        type="xgb",
        params={"n_estimators": 300, "learning_rate": 0.05, "max_depth": 6},
    ),
    ModelConfig(
        name="catboost",
        type="cat",
        params={"iterations": 400, "learning_rate": 0.05, "depth": 6},
    ),
    ModelConfig(
        name="random_forest",
        type="rf",
        params={"n_estimators": 400, "max_depth": 20, "n_jobs": -1},
    ),
    ModelConfig(
        name="extra_trees",
        type="extra",
        params={"n_estimators": 400, "max_depth": 20, "n_jobs": -1},
    ),
    ModelConfig(
        name="gradient_boosting",
        type="gbr",
        params={"n_estimators": 300, "learning_rate": 0.05},
    ),
    ModelConfig(
        name="ridge_regression",
        type="ridge",
        params={"alpha": 1.0},
    ),
    ModelConfig(
        name="linear_regression",
        type="linreg",
        params={},
    ),
    ModelConfig(
        name="gru",
        type="gru",
        params={"units": 64, "epochs": 15, "batch_size": 64},
    ),
    ModelConfig(
        name="lstm",
        type="lstm",
        params={"units": 64, "epochs": 15, "batch_size": 64},
    ),
]
