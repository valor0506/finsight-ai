#!/bin/bash
# Start Celery background worker (concurrency 1 for free-tier memory safety)
celery -A tasks.celery_app.celery_app worker --loglevel=info --concurrency=1 &

# Start FastAPI web server
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
