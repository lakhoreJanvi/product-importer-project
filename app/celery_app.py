from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

CELERY_BROKER_URL = os.getenv("REDIS_URL")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL")

celery = Celery(
    "product_importer",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

celery.conf.update(
    task_soft_time_limit=3600,
    task_time_limit=7200,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

celery.conf.task_routes = {
    "app.tasks.*": {"queue": "import_queue"},
}

celery.autodiscover_tasks(["app"])