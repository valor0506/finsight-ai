"""
tasks/celery_app.py
"""
import ssl
import certifi
from celery import Celery
from core.config import get_settings

settings = get_settings()

_ssl_config = {
    "ssl_cert_reqs": ssl.CERT_REQUIRED,
    "ssl_ca_certs":  certifi.where(),
}

celery_app = Celery(
    "finsight",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks.report_task"],          # ← FIX: was "tasks.task_test"
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    timezone="Asia/Kolkata",
    enable_utc=True,

    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    task_max_retries=3,
    task_default_retry_delay=60,
    result_expires=86400,

    broker_connection_retry_on_startup=True,
    broker_use_ssl=_ssl_config,
    redis_backend_use_ssl=_ssl_config,
)