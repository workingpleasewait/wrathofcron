#!/bin/bash
# AI Agent Coordination Example Script
# 
# This script demonstrates best practices for coordinating multiple AI agents
# using the BBS system for task distribution and status monitoring.

# Get the directory of this script and source BBS helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BBS_SCRIPT="$SCRIPT_DIR/../bbs.sh"

# Source the BBS helpers
if [ -f "$BBS_SCRIPT" ]; then
    source "$BBS_SCRIPT"
else
    echo "Error: Cannot find bbs.sh at $BBS_SCRIPT"
    echo "Make sure you're running this from the correct directory"
    exit 1
fi

# Configuration
AGENT_ID="${AGENT_NAME:-$(hostname)-coordinator}"
CHECK_INTERVAL=10  # Check for tasks every 10 seconds
MAX_SILENCE_MINUTES=5  # Consider agent dead after 5 minutes of silence

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")  echo -e "${GREEN}[INFO]${NC}  [$timestamp] $message" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC}  [$timestamp] $message" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} [$timestamp] $message" ;;
        "DEBUG") echo -e "${BLUE}[DEBUG]${NC} [$timestamp] $message" ;;
        *)       echo "[$timestamp] $message" ;;
    esac
}

# Function to post a task to the queue
post_task() {
    local task_id="$1"
    local task_type="$2"
    local task_data="$3"
    local priority="${4:-normal}"
    
    local task_message="Task ID: $task_id, Type: $task_type, Priority: $priority"
    local task_details="Data: $task_data"
    
    if python3 "$SCRIPT_DIR/../bbs.py" post "$task_message"$'\n'"$task_details" -s "TASK:$task_type" --author "$AGENT_ID" --quiet; then
        log "INFO" "Posted task $task_id ($task_type) with priority $priority"
        return 0
    else
        log "ERROR" "Failed to post task $task_id"
        return 1
    fi
}

# Function to claim a task
claim_task() {
    local task_id="$1"
    
    if python3 "$SCRIPT_DIR/../bbs.py" post "Agent $AGENT_ID claiming task $task_id" -s "CLAIM:$task_id" --author "$AGENT_ID" --quiet; then
        log "INFO" "Claimed task $task_id"
        return 0
    else
        log "ERROR" "Failed to claim task $task_id"
        return 1
    fi
}

# Function to complete a task
complete_task() {
    local task_id="$1"
    local result="$2"
    
    if python3 "$SCRIPT_DIR/../bbs.py" post "Task $task_id completed. Result: $result" -s "COMPLETE:$task_id" --author "$AGENT_ID" --quiet; then
        log "INFO" "Completed task $task_id with result: $result"
        return 0
    else
        log "ERROR" "Failed to mark task $task_id as complete"
        return 1
    fi
}

# Function to send heartbeat
send_heartbeat() {
    local status_info="${1:-healthy}"
    
    if python3 "$SCRIPT_DIR/../bbs.py" post "Heartbeat from $AGENT_ID: $status_info" -s "HEARTBEAT:$AGENT_ID" --author "$AGENT_ID" --quiet; then
        log "DEBUG" "Sent heartbeat: $status_info"
        return 0
    else
        log "WARN" "Failed to send heartbeat"
        return 1
    fi
}

# Function to check for available tasks
check_for_tasks() {
    local since_time=$(date -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -v-1H '+%Y-%m-%dT%H:%M:%SZ')
    
    # Get recent messages and filter for unclaimed tasks
    local tasks=$(python3 "$SCRIPT_DIR/../bbs.py" read --since "$since_time" --format json 2>/dev/null | \
                  jq -r '.[] | select(.subject | startswith("TASK:")) | .subject + "|" + .message_id' 2>/dev/null)
    
    if [ -n "$tasks" ]; then
        echo "$tasks"
    fi
}

# Function to check agent health
check_agent_health() {
    local since_time=$(date -d "${MAX_SILENCE_MINUTES} minutes ago" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || \
                      date -v-${MAX_SILENCE_MINUTES}M '+%Y-%m-%dT%H:%M:%SZ')
    
    local active_agents=$(python3 "$SCRIPT_DIR/../bbs.py" read --since "$since_time" --format json 2>/dev/null | \
                         jq -r '.[] | select(.subject | startswith("HEARTBEAT:")) | .subject' 2>/dev/null | \
                         sed 's/HEARTBEAT://' | sort -u)
    
    if [ -n "$active_agents" ]; then
        log "INFO" "Active agents: $(echo $active_agents | tr '\n' ' ')"
    else
        log "WARN" "No active agents detected in last $MAX_SILENCE_MINUTES minutes"
    fi
}

# Function to simulate task processing
process_task() {
    local task_id="$1"
    local task_type="$2"
    
    log "INFO" "Processing task $task_id ($task_type)..."
    
    # Simulate different types of work
    case "$task_type" in
        "data_analysis")
            sleep 5
            complete_task "$task_id" "Analysis completed: Trend is bullish"
            ;;
        "market_check")
            sleep 3
            complete_task "$task_id" "Market check completed: All systems normal"
            ;;
        "health_check")
            sleep 2
            complete_task "$task_id" "Health check passed: All services running"
            ;;
        *)
            sleep 4
            complete_task "$task_id" "Generic task completed successfully"
            ;;
    esac
}

# Function to run agent worker loop
run_worker() {
    log "INFO" "Starting agent worker: $AGENT_ID"
    send_heartbeat "Starting up"
    
    local heartbeat_counter=0
    
    while true; do
        # Send heartbeat every 30 seconds (3 cycles)
        if [ $((heartbeat_counter % 3)) -eq 0 ]; then
            local cpu_usage=$(top -l 1 -n 0 | grep "CPU usage" | awk '{print $3}' 2>/dev/null || echo "N/A")
            send_heartbeat "CPU: $cpu_usage"
        fi
        
        # Check for available tasks
        local available_tasks=$(check_for_tasks)
        
        if [ -n "$available_tasks" ]; then
            # Process first available task
            local task_line=$(echo "$available_tasks" | head -n 1)
            local task_subject=$(echo "$task_line" | cut -d'|' -f1)
            local task_type=$(echo "$task_subject" | sed 's/TASK://')
            local task_id="task_$(date +%s)"
            
            if claim_task "$task_id"; then
                process_task "$task_id" "$task_type"
            fi
        else
            log "DEBUG" "No tasks available"
        fi
        
        heartbeat_counter=$((heartbeat_counter + 1))
        sleep "$CHECK_INTERVAL"
    done
}

# Function to run coordinator (posts tasks and monitors health)
run_coordinator() {
    log "INFO" "Starting coordinator: $AGENT_ID"
    
    # Post some example tasks
    post_task "001" "data_analysis" "Analyze BTC price trends" "high"
    post_task "002" "market_check" "Check overall market health" "normal"
    post_task "003" "health_check" "Verify all systems" "low"
    
    local cycle=0
    
    while true; do
        # Check agent health every 5 cycles (50 seconds)
        if [ $((cycle % 5)) -eq 0 ]; then
            check_agent_health
        fi
        
        # Post a new task every 10 cycles (100 seconds)
        if [ $((cycle % 10)) -eq 0 ]; then
            local task_id="periodic_$(date +%s)"
            post_task "$task_id" "health_check" "Periodic system check" "normal"
        fi
        
        cycle=$((cycle + 1))
        sleep "$CHECK_INTERVAL"
    done
}

# Function to monitor the BBS (read-only observer)
run_monitor() {
    log "INFO" "Starting monitor: $AGENT_ID"
    
    # Watch for important messages
    python3 "$SCRIPT_DIR/../bbs.py" read --format json | \
    jq -r '.[] | select(.subject | test("^(TASK|CLAIM|COMPLETE|ERROR|HEARTBEAT):")) | 
           .timestamp + " [" + .subject + "] " + .author + ": " + .message' | \
    while IFS= read -r line; do
        echo -e "${BLUE}[MONITOR]${NC} $line"
    done
}

# Function to show usage
show_usage() {
    echo "AI Agent Coordination Example"
    echo ""
    echo "Usage: $0 [mode]"
    echo ""
    echo "Modes:"
    echo "  worker      Run as task worker (processes tasks from queue)"
    echo "  coordinator Run as coordinator (posts tasks and monitors)"
    echo "  monitor     Run as observer (read-only monitoring)"
    echo "  demo        Run a quick demo of all functions"
    echo "  help        Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  AGENT_NAME  Set the agent identifier (default: hostname-coordinator)"
    echo ""
    echo "Examples:"
    echo "  $0 worker                    # Run as worker agent"
    echo "  AGENT_NAME=analyzer $0 worker # Run as 'analyzer' worker"
    echo "  $0 coordinator               # Run as task coordinator"
    echo "  $0 monitor                   # Monitor all BBS activity"
}

# Function to run a quick demo
run_demo() {
    log "INFO" "Running coordination demo..."
    
    # Post some example tasks
    post_task "demo_001" "data_analysis" "Demo: Analyze sample data" "high"
    post_task "demo_002" "market_check" "Demo: Check demo market" "normal"
    
    # Send a heartbeat
    send_heartbeat "Demo mode: CPU 25%, Memory 1.2GB"
    
    # Claim and complete a task
    claim_task "demo_001"
    sleep 2
    complete_task "demo_001" "Demo analysis completed successfully"
    
    # Check agent health
    check_agent_health
    
    log "INFO" "Demo completed! Check the BBS with: python3 ../bbs.py tail -n 10"
}

# Main script logic
MODE="${1:-help}"

case "$MODE" in
    "worker")
        run_worker
        ;;
    "coordinator")
        run_coordinator
        ;;
    "monitor")
        run_monitor
        ;;
    "demo")
        run_demo
        ;;
    "help"|*)
        show_usage
        ;;
esac
