from celery import Celery
from celery.schedules import crontab
from app.infra.config.settings import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.infra.queue.tasks"]
)

celery_app.conf.beat_schedule = {
    "sync-provider-models-every-24h": {
        "task": "sync_provider_models_task",
        "schedule": crontab(hour=3, minute=0),  # Run at 3 AM daily
    },
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
)