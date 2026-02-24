from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "fiscalspy",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"]
)

celery_app.conf.beat_schedule = {
    "sincronizar-sefaz-a-cada-5-minutos": {
        "task": "app.workers.tasks.sincronizar_todas_empresas",
        "schedule": crontab(minute="*/5"),
    },
}

celery_app.conf.timezone = "America/Sao_Paulo"
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
