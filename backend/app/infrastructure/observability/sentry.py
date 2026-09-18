import sentry_sdk


def configure_sentry(dsn: str | None, *, environment: str) -> None:
    if not dsn:
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
