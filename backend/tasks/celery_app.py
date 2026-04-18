"""
tasks/celery_app.py

Celery configuration.

Key decisions:
- broker_use_ssl with CERT_REQUIRED: actually validates Upstash's SSL cert
- worker_prefetch_multiplier=1: take one task at a time (our tasks are 60s+)
- task_acks_late=True: don't mark task done until it actually finishes
- pool=solo set via command line on Windows (prefork not supported on Windows)
"""
import ssl
from celery import Celery
from core.config import get_settings
import certifi
settings = get_settings()

# Build SSL config that actually validates the certificate
# ssl.CERT_REQUIRED = verify the server's certificate against CA bundle
# ssl.get_default_verify_paths().cafile = system's trusted CA certificates
_ssl_config = {
    "ssl_cert_reqs": ssl.CERT_REQUIRED,
    "ssl_ca_certs": certifi.where()
}

celery_app = Celery(
    "finsight",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks.task_test"],
)

celery_app.conf.update(
    # Serialization — JSON is human-readable and safe
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="Asia/Kolkata",
    enable_utc=True,

    # Task behaviour
    task_track_started=True,        # PENDING → STARTED → SUCCESS/FAILURE
    task_acks_late=True,            # acknowledge only after completion
    worker_prefetch_multiplier=1,   # one task at a time per worker

    # Retry config
    task_max_retries=3,
    task_default_retry_delay=60,

    # Result expiry — keep results 24 hours
    result_expires=86400,

    # Startup retry (fixes deprecation warning)
    broker_connection_retry_on_startup=True,

    # SSL — properly validated (fixes security warning)
    broker_use_ssl=_ssl_config,
    redis_backend_use_ssl=_ssl_config,
)