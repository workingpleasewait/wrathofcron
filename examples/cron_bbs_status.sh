#!/bin/bash
# Example cron script for posting system status to bulletin board
# 
# Add to crontab with: crontab -e
# Example cron entries:
#   # Post system status every 15 minutes
#   */15 * * * * /path/to/examples/cron_bbs_status.sh
#   
#   # Post daily summary at 8 AM
#   0 8 * * * /path/to/examples/cron_bbs_status.sh daily

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BBS_SCRIPT="$SCRIPT_DIR/../bbs.sh"

# Source the BBS helpers
if [ -f "$BBS_SCRIPT" ]; then
    source "$BBS_SCRIPT"
else
    echo "Error: Cannot find bbs.sh at $BBS_SCRIPT"
    exit 1
fi

# Function to post system metrics
post_system_status() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # System uptime
    local uptime_info=$(uptime | sed 's/.*up \([^,]*\),.*/\1/')
    bbs_post "[$timestamp] System uptime: $uptime_info" system
    
    # Memory usage
    local memory_info=$(free -h | awk 'NR==2{printf "Memory: %s/%s (%.1f%%)", $3,$2,$3*100/$2}')
    bbs_post "[$timestamp] $memory_info" system
    
    # Disk usage for root partition
    local disk_info=$(df -h / | awk 'NR==2{printf "Disk: %s/%s (%s)", $3,$2,$5}')
    bbs_post "[$timestamp] $disk_info" system
    
    # Load average
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | sed 's/^ *//')
    bbs_post "[$timestamp] Load average:$load_avg" system
}

# Function to post daily summary
post_daily_summary() {
    local date=$(date '+%Y-%m-%d')
    
    # System information
    local hostname=$(hostname)
    local os_info=$(uname -a | awk '{print $1, $3}')
    
    bbs_post "=== Daily Summary for $date ===" system
    bbs_post "Host: $hostname ($os_info)" system
    
    # Post current status
    post_system_status
    
    # Check for any service failures (if systemctl is available)
    if command -v systemctl >/dev/null 2>&1; then
        local failed_services=$(systemctl --failed --no-legend | wc -l)
        if [ "$failed_services" -gt 0 ]; then
            bbs_post "⚠️  Warning: $failed_services failed service(s) detected" alerts
        else
            bbs_post "✅ All services running normally" system
        fi
    fi
    
    bbs_post "=== End Daily Summary ===" system
}

# Main logic
case "${1:-status}" in
    "daily")
        post_daily_summary
        ;;
    "status"|*)
        post_system_status
        ;;
esac
