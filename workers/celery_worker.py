from celery import Celery

celery = Celery(
    "worker",
    broker="redis://localhost:6384/0",
    backend="redis://localhost:6384/0"
)

celery.autodiscover_tasks(["app.workers.tasks"])