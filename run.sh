#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_FILE="$SCRIPT_DIR/logs/agent.log"
mkdir -p "$SCRIPT_DIR/logs"

echo "=== $(date) ===" >> "$LOG_FILE"
"$SCRIPT_DIR/.venv/bin/python" main.py >> "$LOG_FILE" 2>&1
