from pathlib import Path

import pandas as pd

from app.domain.contracts import ForecastModel
from app.ml.demand.baseline import BaselineForecaster


def build_forecaster(
    rows: pd.DataFrame,
    *,
    preferred: str = "baseline",
    min_training_rows: int = 60,
    model_path: str | Path | None = None,
) -> ForecastModel:
    if preferred == "lightgbm" and len(rows) >= min_training_rows:
        from app.ml.demand.lightgbm_model import LightGBMForecaster

        model = LightGBMForecaster(model_path)
        if model.model is None:
            model.fit(rows)
        return model
    model = BaselineForecaster()
    model.fit(rows)
    return model
