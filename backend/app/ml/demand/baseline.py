import math
from typing import Any

import pandas as pd

from app.domain.entities import ForecastResult


class BaselineForecaster:
    name = "seasonal-naive-7d"

    def __init__(self) -> None:
        self.history: pd.Series | None = None

    def fit(self, rows: Any, target: Any = None) -> None:
        if isinstance(rows, pd.DataFrame):
            series = rows["sales"] if target is None else target
        else:
            series = target if target is not None else rows
        self.history = pd.Series(series, dtype=float).dropna()
        if self.history.empty:
            raise ValueError("At least one sales observation is required")

    def predict(self, rows: Any = None, *, horizon_days: int = 1) -> ForecastResult:
        if rows is not None:
            self.fit(rows)
        if self.history is None or self.history.empty:
            raise ValueError("Forecaster has not been fitted")
        window = self.history.tail(min(7, len(self.history)))
        daily = max(0.0, float(window.mean()))
        variation = float(window.std(ddof=0)) if len(window) > 1 else daily
        coefficient = variation / daily if daily else 1.0
        confidence = max(0.2, min(0.9, 1.0 / (1.0 + coefficient)))
        predicted = math.ceil(daily * horizon_days * 1000) / 1000
        return ForecastResult(
            predicted_demand=predicted,
            confidence=round(confidence, 4),
            forecast_horizon_days=horizon_days,
            model_name=self.name,
            feature_snapshot={
                "observations": int(len(self.history)),
                "seasonal_window": [float(value) for value in window],
                "daily_mean": round(daily, 4),
            },
        )
