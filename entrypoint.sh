#!/bin/sh
set -e

INTERVAL=${RUN_INTERVAL_SECONDS:-3600}

echo "Mail agent starting. Run interval: ${INTERVAL}s"

while true; do
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Running agent..."
    python main.py
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Done. Sleeping ${INTERVAL}s..."
    sleep "$INTERVAL"
done
