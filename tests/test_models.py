import numpy as np
import pandas as pd

from src.models.model_configs import MODEL_CONFIGS
from src.models.train import train_model


def test_model_training_smoke():
    config = next(c for c in MODEL_CONFIGS if c.type == "rf")
    X = pd.DataFrame(np.random.rand(200, 10))
    y = pd.DataFrame(np.random.rand(200, 72))
    model, preds, y_true = train_model(config, X, y, horizon=72)

    assert preds.shape[1] == 72
    assert y_true.shape[1] == 72
