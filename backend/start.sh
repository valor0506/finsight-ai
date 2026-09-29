#!/bin/bash
# Start Celery background worker
celery -A tasks.celery_app.celery_app worker --loglevel=info --concurrency=2 &

# Start FastAPI web server
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
