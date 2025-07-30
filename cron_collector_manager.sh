#!/bin/bash

set -euo pipefail

# Cron Collector Management Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COLLECTOR_SCRIPT="$SCRIPT_DIR/cron_collector.py"
PID_FILE="$HOME/.cron_dash/collector.pid"
LOG_FILE="$HOME/.cron_dash/collector.log"

start_collector() {
    if [ -f "$PID_FILE" ]; then
        if PID=$(cat "$PID_FILE") && kill -0 "$PID" 2>/dev/null; then
            echo "📊 Cron collector is already running (PID: $PID)"
            return 0
        fi
    fi
    
    echo "🚀 Starting cron collector daemon..."
    cd "$SCRIPT_DIR"
    
    # Start the collector in daemon mode
    nohup python3 "$COLLECTOR_SCRIPT" --daemon > /dev/null 2>&1 &
    echo $! > "$PID_FILE"
    
    sleep 2
    
    if [ -f "$PID_FILE" ] && PID=$(cat "$PID_FILE") && kill -0 "$PID" 2>/dev/null; then
        echo "✅ Cron collector started successfully (PID: $PID)"
        echo "📋 Log file: $LOG_FILE"
        echo "💾 Database: ~/.cron_dash/ladder.db"
    else
        echo "❌ Failed to start cron collector"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_collector() {
    if [ -f "$PID_FILE" ]; then
        if PID=$(cat "$PID_FILE"); then
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID"
                echo "🛑 Stopped cron collector (PID: $PID)"
            else
                echo "⚠️  Process $PID not found"
            fi
        else
            echo "⚠️  Invalid PID file content"
        fi
        rm -f "$PID_FILE"
    else
        echo "⚠️  No cron collector running"
    fi
}

status_collector() {
    if [ -f "$PID_FILE" ] && PID=$(cat "$PID_FILE") && kill -0 "$PID" 2>/dev/null; then
        echo "📊 Cron collector is running (PID: $PID)"
        echo "📁 Watching: ~/logs/ladder.jsonl"
        echo "💾 Database: ~/.cron_dash/ladder.db"
        echo "📋 Log file: $LOG_FILE"
        
        # Show recent stats
        echo ""
        python3 "$COLLECTOR_SCRIPT" --stats
    else
        echo "❌ Cron collector is not running"
        if [ -f "$PID_FILE" ]; then
            rm -f "$PID_FILE"
        fi
    fi
}

show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "📋 Recent cron collector activity:"
        echo "=================================="
        tail -F -20 "$LOG_FILE"
    else
        echo "📋 No log file found yet"
    fi
}

parse_existing() {
    echo "🔄 Parsing existing entries from ladder.jsonl..."
    cd "$SCRIPT_DIR"
    python3 "$COLLECTOR_SCRIPT" --parse-existing
}

show_stats() {
    echo "📊 Current statistics:"
    cd "$SCRIPT_DIR"
    python3 "$COLLECTOR_SCRIPT" --stats
}

install_cron() {
    echo "⚙️  Installing cron collector as a cron job..."
    
    # Create a cron entry to start the collector on reboot
    CRON_ENTRY="@reboot cd \"$SCRIPT_DIR\" && ./cron_collector_manager.sh start"
    
    # Check if entry already exists
    if crontab -l 2>/dev/null | grep -q "cron_collector_manager.sh start"; then
        echo "✅ Cron entry already exists"
    else
        # Add the cron entry
        (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
        echo "✅ Cron entry added - collector will start on system reboot"
    fi
    
    # Also start it now if not running
    if ! ([ -f "$PID_FILE" ] && PID=$(cat "$PID_FILE") && kill -0 "$PID" 2>/dev/null); then
        start_collector
    fi
}

case "$1" in
    start)
        start_collector
        ;;
    stop)
        stop_collector
        ;;
    status)
        status_collector
        ;;
    restart)
        stop_collector
        sleep 2
        start_collector
        ;;
    logs)
        show_logs
        ;;
    parse)
        parse_existing
        ;;
    stats)
        show_stats
        ;;
    install)
        install_cron
        ;;
    *)
        echo "Cron Collector Management"
        echo "========================="
        echo "Usage: $0 {start|stop|status|restart|logs|parse|stats|install}"
        echo ""
        echo "Commands:"
        echo "  start     - Start the collector daemon"
        echo "  stop      - Stop the collector daemon"
        echo "  status    - Check daemon status and show stats"
        echo "  restart   - Restart the collector daemon"
        echo "  logs      - Show recent collector logs"
        echo "  parse     - Parse existing entries from ladder.jsonl"
        echo "  stats     - Show current statistics"
        echo "  install   - Install as cron job (auto-start on reboot)"
        echo ""
        echo "Features:"
        echo "  • Watches ~/logs/ladder.jsonl for new entries"
        echo "  • Stores data in ~/.cron_dash/ladder.db SQLite database"
        echo "  • Computes success rates and runtime statistics"
        echo "  • Sends macOS notifications for failed runs (exit != 0)"
        echo "  • Provides detailed analytics and monitoring"
        exit 1
        ;;
esac
