#!/bin/bash
# Auto-sync cron jobs when changes are detected
set -euo pipefail

# Get the absolute path of the script directory (cross-platform)
if [ "$(uname)" = "Darwin" ]; then
    # macOS doesn't have readlink -f, use a different approach
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
else
    # Linux has readlink -f
    SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
fi

# Set paths relative to script directory
CRON_MANAGER="$SCRIPT_DIR/cron-manager.sh"
LAST_CHECK_FILE="$SCRIPT_DIR/.last-cron-check"
SHARED_CRONTAB="$SCRIPT_DIR/shared-crontab.txt"
CRON_JOBS_DIR="$SCRIPT_DIR/cron-jobs"

# Create last check file if it doesn't exist
if [ ! -f "$LAST_CHECK_FILE" ]; then
    touch "$LAST_CHECK_FILE"
fi

# Check if shared cron file has been updated
if [ "$SHARED_CRONTAB" -nt "$LAST_CHECK_FILE" ] || 
   [ "$CRON_JOBS_DIR" -nt "$LAST_CHECK_FILE" ]; then
    echo "🔄 Cron files updated, syncing..."
    "$CRON_MANAGER" install
    touch "$LAST_CHECK_FILE"
fi
