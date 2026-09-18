import pandas as pd

from app.domain.contracts import ForecastModel


def forecast_demand(model: ForecastModel, history: list[dict], horizon_days: int) -> dict:
    return model.predict(pd.DataFrame(history), horizon_days=horizon_days).model_dump(mode="json")
