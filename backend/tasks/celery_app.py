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

is_ssl = settings.redis_url.startswith("rediss://")

celery_app = Celery(
    "finsight",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks.report_task"],
)

celery_conf = {
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",

    "timezone": "Asia/Kolkata",
    "enable_utc": True,

    "task_track_started": True,
    "task_acks_late": True,
    "worker_prefetch_multiplier": 1,

    "task_max_retries": 3,
    "task_default_retry_delay": 60,
    "result_expires": 86400,

    "broker_connection_retry_on_startup": True,
}

if is_ssl:
    celery_conf["broker_use_ssl"] = _ssl_config
    celery_conf["redis_backend_use_ssl"] = _ssl_config

celery_app.conf.update(**celery_conf)