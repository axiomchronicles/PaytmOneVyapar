from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

from app.domain.entities import ForecastResult
from app.ml.demand.features import FEATURE_COLUMNS, build_features


class LightGBMForecaster:
    name = "lightgbm-demand-v1"

    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.model: lgb.LGBMRegressor | None = None
        if self.model_path and self.model_path.exists():
            self.model = lgb.LGBMRegressor()
            self.model._Booster = lgb.Booster(model_file=str(self.model_path))
            self.model.fitted_ = True

    def fit(self, rows: Any, target: Any = None) -> None:
        frame = build_features(pd.DataFrame(rows)).dropna(subset=["lag_7"])
        if len(frame) < 20:
            raise ValueError("LightGBM requires at least 20 usable training rows")
        y = frame["sales"] if target is None else np.asarray(target)[-len(frame) :]
        self.model = lgb.LGBMRegressor(
            objective="regression_l1",
            n_estimators=120,
            learning_rate=0.04,
            num_leaves=15,
            random_state=42,
            verbosity=-1,
        )
        self.model.fit(frame[FEATURE_COLUMNS], y)

    def predict(self, rows: Any, *, horizon_days: int = 1) -> ForecastResult:
        if self.model is None:
            raise ValueError("LightGBM model has not been fitted or loaded")
        frame = build_features(pd.DataFrame(rows)).ffill().fillna(0)
        prediction = max(0.0, float(self.model.predict(frame[FEATURE_COLUMNS].tail(1))[0]))
        snapshot = {
            key: float(value) if isinstance(value, (int, float, np.number)) else str(value)
            for key, value in frame[FEATURE_COLUMNS].tail(1).iloc[0].items()
        }
        snapshot["confidence_calibrated"] = False
        return ForecastResult(
            predicted_demand=round(prediction * horizon_days, 3),
            confidence=0.0,
            forecast_horizon_days=horizon_days,
            model_name=self.name,
            feature_snapshot=snapshot,
        )

    def save(self, path: str | Path | None = None) -> None:
        destination = Path(path) if path else self.model_path
        if destination is None or self.model is None:
            raise ValueError("A fitted model and destination path are required")
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.model.booster_.save_model(str(destination))
