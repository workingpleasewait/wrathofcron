#!/bin/bash
# Auto-sync cron jobs when changes are detected

CRON_MANAGER="./cron-manager.sh"
LAST_CHECK_FILE=".last-cron-check"

if [ ! -f "$LAST_CHECK_FILE" ]; then
    touch "$LAST_CHECK_FILE"
fi

# Check if shared cron file has been updated
if [ "shared-crontab.txt" -nt "$LAST_CHECK_FILE" ] || 
   [ "cron-jobs/" -nt "$LAST_CHECK_FILE" ]; then
    echo "🔄 Cron files updated, syncing..."
    "$CRON_MANAGER" install
    touch "$LAST_CHECK_FILE"
fi
