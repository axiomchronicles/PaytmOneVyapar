import pandas as pd

from app.ml.demand.baseline import BaselineForecaster
from app.ml.demand.features import build_features
from app.ml.demand.lightgbm_model import LightGBMForecaster


def test_baseline_forecast_is_deterministic() -> None:
    rows = pd.DataFrame({"sales": [1, 2, 3, 4, 5, 6, 7]})
    model = BaselineForecaster()
    first = model.predict(rows, horizon_days=2)
    second = model.predict(rows, horizon_days=2)
    assert first.predicted_demand == 8
    assert first == second
    assert first.model_name == "seasonal-naive-7d"


def test_feature_pipeline_adds_lags_calendar_and_signals() -> None:
    rows = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=10, tz="UTC"),
            "sales": range(10),
            "inventory": [20] * 10,
            "price": [100] * 10,
        }
    )
    features = build_features(rows)
    assert features.iloc[7]["lag_7"] == 0
    assert {"rolling_7", "day_of_week", "festival_flag", "temperature_c"} <= set(features.columns)


def test_lightgbm_path_fits_only_when_explicitly_called() -> None:
    rows = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=40, tz="UTC"),
            "sales": [4 + index % 7 for index in range(40)],
            "inventory": [20] * 40,
            "price": [100] * 40,
        }
    )
    model = LightGBMForecaster()
    model.fit(rows)
    result = model.predict(rows, horizon_days=2)
    assert result.predicted_demand >= 0
    assert result.model_name == "lightgbm-demand-v1"
    assert result.feature_snapshot["confidence_calibrated"] is False
