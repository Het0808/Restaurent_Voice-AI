#!/bin/sh
set -eu
python scripts/wait_for_postgres.py
python scripts/wait_for_redis.py
python scripts/migrate.py
PROXY_FLAG=--no-proxy-headers
if [ "${TRUST_PROXY_HEADERS:-false}" = "true" ]; then PROXY_FLAG=--proxy-headers; fi
exec uvicorn restaurant_voice_ai.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 "$PROXY_FLAG"
