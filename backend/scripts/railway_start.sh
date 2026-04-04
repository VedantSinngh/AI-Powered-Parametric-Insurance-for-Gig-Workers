#!/usr/bin/env bash
set -euo pipefail

role="${SERVICE_ROLE:-api}"

case "$role" in
  api)
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
    ;;
  worker)
    exec celery -A app.tasks.celery_app worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-4}"
    ;;
  beat)
    exec celery -A app.tasks.celery_app beat --loglevel=info
    ;;
  *)
    echo "Unknown SERVICE_ROLE: $role"
    echo "Expected one of: api, worker, beat"
    exit 1
    ;;
esac
