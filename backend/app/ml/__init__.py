def build_forecaster(*args, **kwargs):
    from app.ml.demand.forecaster import build_forecaster as factory

    return factory(*args, **kwargs)


__all__ = ["build_forecaster"]
