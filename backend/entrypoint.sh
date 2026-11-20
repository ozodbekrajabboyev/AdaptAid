#!/bin/sh
# Apply migrations, then serve. One worker: the nightly scheduler must run in exactly one process.
set -e
python -m app.cli migrate
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips="*"
