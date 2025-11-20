from celery import Celery
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

CELERY_BROKER_URL = os.getenv("REDIS_URL")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL")

celery = Celery(
    "product_importer",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

# @celery.task()
# def process_csv(path):
#     total_rows = 0
#     for chunk in pd.read_csv(path, chunksize=50000):
#         total_rows += len(chunk)

#     return {"processed": total_rows}

celery.conf.task_routes = {
    "app.tasks.*": {"queue": "import_queue"},
}

celery.autodiscover_tasks(["app"])
