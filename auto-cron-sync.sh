#!/bin/bash
# Auto-sync cron jobs when changes are detected
set -euo pipefail

# Get the absolute path of the script directory
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

# Convert all paths to absolute
CRON_MANAGER="$SCRIPT_DIR/cron-manager.sh"
LAST_CHECK_FILE="$SCRIPT_DIR/.last-cron-check"
SHARED_CRONTAB="$SCRIPT_DIR/shared-crontab.txt"
CRON_JOBS_DIR="$SCRIPT_DIR/cron-jobs"

# Create last check file if it doesn't exist
if [ ! -f "$LAST_CHECK_FILE" ]; then
    touch "$LAST_CHECK_FILE"
fi

# Convert to absolute paths after ensuring files exist
CRON_MANAGER="$(readlink -f "$CRON_MANAGER")"
LAST_CHECK_FILE="$(readlink -f "$LAST_CHECK_FILE")"
SHARED_CRONTAB="$(readlink -f "$SHARED_CRONTAB")"
CRON_JOBS_DIR="$(readlink -f "$CRON_JOBS_DIR")"

# Check if shared cron file has been updated
if [ "$SHARED_CRONTAB" -nt "$LAST_CHECK_FILE" ] || 
   [ "$CRON_JOBS_DIR" -nt "$LAST_CHECK_FILE" ]; then
    echo "🔄 Cron files updated, syncing..."
    "$CRON_MANAGER" install
    touch "$LAST_CHECK_FILE"
fi
