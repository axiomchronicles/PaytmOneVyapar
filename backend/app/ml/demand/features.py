import pandas as pd

FEATURE_COLUMNS = [
    "lag_1",
    "lag_7",
    "rolling_7",
    "rolling_28",
    "day_of_week",
    "month",
    "festival_flag",
    "temperature_c",
    "local_event_flag",
    "price",
    "promotion_flag",
    "inventory",
]


def build_features(rows: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "sales", "inventory", "price"}
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"Missing forecasting columns: {', '.join(sorted(missing))}")
    frame = rows.copy().sort_values("date")
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    frame["day_of_week"] = frame["date"].dt.dayofweek
    frame["month"] = frame["date"].dt.month
    frame["lag_1"] = frame["sales"].shift(1)
    frame["lag_7"] = frame["sales"].shift(7)
    frame["rolling_7"] = frame["sales"].shift(1).rolling(7, min_periods=1).mean()
    frame["rolling_28"] = frame["sales"].shift(1).rolling(28, min_periods=1).mean()
    for column in ("festival_flag", "local_event_flag", "promotion_flag"):
        if column not in frame:
            frame[column] = 0
    if "temperature_c" not in frame:
        frame["temperature_c"] = frame.get("weather_temperature_c", 25.0)
    return frame
