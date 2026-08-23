#!/bin/sh
set -e

export AUTO_CREATE_TABLES="${AUTO_CREATE_TABLES:-false}"

attempt=1
max_attempts=20
until flask --app run.py db upgrade; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "database migration failed after ${max_attempts} attempts" >&2
    exit 1
  fi
  echo "database is not ready; migration retry ${attempt}/${max_attempts} in 2 seconds" >&2
  attempt=$((attempt + 1))
  sleep 2
done

exec gunicorn \
  --bind 0.0.0.0:5000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --access-logfile - \
  --error-logfile - \
  run:app
