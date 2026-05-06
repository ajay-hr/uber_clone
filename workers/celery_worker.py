from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6384/0")

celery = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery.autodiscover_tasks(["app.workers.tasks"])
