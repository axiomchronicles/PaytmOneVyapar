from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import get_settings
from app.workers.jobs import publish_outbox


class WorkerSettings:
    functions = [publish_outbox]
    cron_jobs = [cron(publish_outbox, second={0, 10, 20, 30, 40, 50})]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 20
    job_timeout = 60
