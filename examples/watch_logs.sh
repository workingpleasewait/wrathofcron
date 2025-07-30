#!/bin/bash
# Example watch script that monitors log files and posts alerts to bulletin board
#
# Usage:
#   ./watch_logs.sh [log_file] [board_name]
#
# Examples:
#   ./watch_logs.sh /var/log/syslog alerts
#   ./watch_logs.sh ./app.log trading
#   ./watch_logs.sh  # uses default log file

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

# Configuration
LOG_FILE="${1:-/var/log/system.log}"  # Default log file (adjust for your system)
BOARD_NAME="${2:-alerts}"             # Default board name
CHECK_INTERVAL=5                      # Check every 5 seconds

# Alert patterns (case-insensitive)
ERROR_PATTERNS="error|critical|fatal|fail|exception|panic|segfault"
WARNING_PATTERNS="warning|warn|timeout|retry|deprecated"

# Function to check if log file exists and is readable
check_log_file() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "Error: Log file '$LOG_FILE' does not exist"
        echo "Available log files:"
        ls -la /var/log/ 2>/dev/null | head -10 || echo "Cannot access /var/log/"
        exit 1
    fi
    
    if [ ! -r "$LOG_FILE" ]; then
        echo "Error: Log file '$LOG_FILE' is not readable"
        echo "Try running with sudo or check file permissions"
        exit 1
    fi
}

# Function to process log line and determine alert level
process_log_line() {
    local line="$1"
    local timestamp=$(date '+%H:%M:%S')
    
    # Check for error patterns
    if echo "$line" | grep -iE "$ERROR_PATTERNS" >/dev/null; then
        bbs_post "🚨 [$timestamp] ERROR: $line" "$BOARD_NAME"
        return 0
    fi
    
    # Check for warning patterns
    if echo "$line" | grep -iE "$WARNING_PATTERNS" >/dev/null; then
        bbs_post "⚠️  [$timestamp] WARNING: $line" "$BOARD_NAME"
        return 0
    fi
    
    return 1
}

# Function to start monitoring
start_monitoring() {
    echo "Starting log monitoring..."
    echo "Log file: $LOG_FILE"
    echo "Board: $BOARD_NAME"
    echo "Check interval: ${CHECK_INTERVAL}s"
    echo "Press Ctrl+C to stop"
    echo "----------------------------------------"
    
    # Post startup message
    bbs_post "🔍 Log monitoring started for $(basename "$LOG_FILE")" "$BOARD_NAME"
    
    # Use tail -f to follow the log file
    tail -f "$LOG_FILE" | while IFS= read -r line; do
        process_log_line "$line"
    done
}

# Function to test patterns with recent log entries
test_patterns() {
    echo "Testing alert patterns on recent log entries..."
    echo "Log file: $LOG_FILE"
    echo "Recent entries that would trigger alerts:"
    echo "----------------------------------------"
    
    tail -20 "$LOG_FILE" | while IFS= read -r line; do
        if echo "$line" | grep -iE "$ERROR_PATTERNS|$WARNING_PATTERNS" >/dev/null; then
            echo "MATCH: $line"
        fi
    done
    
    echo "----------------------------------------"
    echo "If no matches shown above, try adjusting patterns or check a different log file"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [log_file] [board_name] [command]"
    echo ""
    echo "Commands:"
    echo "  start     Start monitoring (default)"
    echo "  test      Test patterns on recent log entries"
    echo "  help      Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Monitor default log"
    echo "  $0 /var/log/apache2/error.log web    # Monitor Apache errors"
    echo "  $0 ./app.log trading                 # Monitor application log"
    echo "  $0 /var/log/syslog alerts test       # Test patterns"
    echo ""
    echo "Common log files:"
    echo "  macOS: /var/log/system.log"
    echo "  Linux: /var/log/syslog, /var/log/messages"
    echo "  Apache: /var/log/apache2/error.log"
    echo "  Nginx: /var/log/nginx/error.log"
}

# Handle command line arguments
COMMAND="${3:-start}"

case "$COMMAND" in
    "test")
        check_log_file
        test_patterns
        ;;
    "help")
        show_usage
        ;;
    "start"|*)
        check_log_file
        start_monitoring
        ;;
esac
