from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import train_test_split

import lightgbm as lgb
import xgboost as xgb
import catboost as cb
import tensorflow as tf

from .model_configs import ModelConfig


def _build_dl_model(model_type: str, input_shape: Tuple[int, int], output_steps: int, units: int):
    model = tf.keras.Sequential()
    if model_type == "gru":
        model.add(tf.keras.layers.GRU(units, input_shape=input_shape, return_sequences=False))
    else:
        model.add(tf.keras.layers.LSTM(units, input_shape=input_shape, return_sequences=False))
    model.add(tf.keras.layers.Dense(128, activation="relu"))
    model.add(tf.keras.layers.Dense(output_steps))
    model.compile(optimizer="adam", loss="mse")
    return model


def _prepare_sequence_data(
    features: pd.DataFrame, target: pd.Series, lookback: int, horizon: int
) -> Tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    values = features.values
    target_values = target.values
    for idx in range(lookback, len(features) - horizon):
        X.append(values[idx - lookback : idx])
        y.append(target_values[idx : idx + horizon])
    return np.array(X), np.array(y)


def train_model(
    config: ModelConfig,
    X: pd.DataFrame,
    y: pd.DataFrame,
    horizon: int = 72,
    split_ratio: float = 0.9,
) -> Tuple[object, np.ndarray, np.ndarray]:
    if config.type in {"lgbm", "xgb", "cat", "rf", "extra", "gbr", "ridge", "linreg"}:
        if config.type == "lgbm":
            base = lgb.LGBMRegressor(**config.params)
        elif config.type == "xgb":
            base = xgb.XGBRegressor(**config.params)
        elif config.type == "cat":
            base = cb.CatBoostRegressor(**config.params, verbose=False)
        elif config.type == "rf":
            base = RandomForestRegressor(**config.params)
        elif config.type == "extra":
            base = ExtraTreesRegressor(**config.params)
        elif config.type == "ridge":
            base = Ridge(**config.params)
        elif config.type == "linreg":
            base = LinearRegression(**config.params)
        else:
            base = GradientBoostingRegressor(**config.params)

        split_idx = int(len(X) * split_ratio)
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

        if config.type in {"rf", "extra", "ridge", "linreg"}:
            # These estimators handle multi-output targets directly.
            model = base
            model.fit(X_train, y_train)
        else:
            model = MultiOutputRegressor(base)
            model.fit(X_train, y_train)
        preds = model.predict(X_val)
        return model, preds, y_val.values

    lookback = 24
    X_seq, y_seq = _prepare_sequence_data(X, y.iloc[:, 0], lookback, horizon)
    split_idx = int(len(X_seq) * split_ratio)
    X_train, X_val = X_seq[:split_idx], X_seq[split_idx:]
    y_train, y_val = y_seq[:split_idx], y_seq[split_idx:]

    model = _build_dl_model(
        config.type, input_shape=(X_train.shape[1], X_train.shape[2]), output_steps=horizon, units=config.params.get("units", 64)
    )
    model.fit(
        X_train,
        y_train,
        epochs=config.params.get("epochs", 10),
        batch_size=config.params.get("batch_size", 32),
        verbose=0,
    )
    preds = model.predict(X_val)
    return model, preds, y_val
