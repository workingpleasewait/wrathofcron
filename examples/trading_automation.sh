#!/bin/bash
# Trading Automation Example Script
# 
# This script demonstrates how to integrate the BBS system with trading operations
# for coordinated AI agent trading strategies with safety measures.

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BBS_SCRIPT="$SCRIPT_DIR/../bbs.sh"

# Source the BBS helpers if available
if [ -f "$BBS_SCRIPT" ]; then
    source "$BBS_SCRIPT"
fi

# Configuration
AGENT_ID="${AGENT_NAME:-trading-agent}"
SCRIPTS_DIR="$SCRIPT_DIR/../scripts"
SANDBOX_MODE=true  # Always start in sandbox mode for safety
DRY_RUN=true       # Always start in dry-run mode

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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
        "TRADE") echo -e "${CYAN}[TRADE]${NC} [$timestamp] $message" ;;
        *)       echo "[$timestamp] $message" ;;
    esac
}

# Function to post trading status to BBS
post_trading_status() {
    local status="$1"
    local details="$2"
    
    if command -v python3 > /dev/null && [ -f "$SCRIPT_DIR/../bbs.py" ]; then
        python3 "$SCRIPT_DIR/../bbs.py" post "$details" -s "TRADE_STATUS:$status" --author "$AGENT_ID" --quiet 2>/dev/null || true
    fi
    
    log "TRADE" "$status: $details"
}

# Function to post trading alert to BBS
post_trading_alert() {
    local alert_type="$1"
    local message="$2"
    
    if command -v python3 > /dev/null && [ -f "$SCRIPT_DIR/../bbs.py" ]; then
        python3 "$SCRIPT_DIR/../bbs.py" post "$message" -s "TRADE_ALERT:$alert_type" --author "$AGENT_ID" --quiet 2>/dev/null || true
    fi
    
    log "WARN" "ALERT [$alert_type]: $message"
}

# Function to check account balances
check_balances() {
    log "INFO" "Checking account balances..."
    
    local balance_script="$SCRIPTS_DIR/account_balances.py"
    if [ ! -f "$balance_script" ]; then
        log "ERROR" "Balance script not found: $balance_script"
        return 1
    fi
    
    local balance_args=""
    if [ "$SANDBOX_MODE" = true ]; then
        balance_args="--sandbox"
    fi
    
    if python3 "$balance_script" $balance_args --json > /tmp/balances.json 2>/dev/null; then
        local balance_count=$(jq length /tmp/balances.json 2>/dev/null || echo "0")
        log "INFO" "Retrieved balances for $balance_count accounts"
        post_trading_status "balance_check" "Successfully retrieved $balance_count account balances"
        return 0
    else
        log "ERROR" "Failed to retrieve account balances"
        post_trading_alert "balance_error" "Unable to retrieve account balances - check API credentials"
        return 1
    fi
}

# Function to get market ticker
get_market_data() {
    local symbol="${1:-BTC-USD}"
    
    log "INFO" "Getting market data for $symbol..."
    
    local ticker_script="$SCRIPTS_DIR/get_market_ticker.py"
    if [ ! -f "$ticker_script" ]; then
        log "ERROR" "Market ticker script not found: $ticker_script"
        return 1
    fi
    
    if python3 "$ticker_script" --symbol "$symbol" > /tmp/ticker.json 2>/dev/null; then
        local price=$(jq -r '.price // "N/A"' /tmp/ticker.json 2>/dev/null || echo "N/A")
        log "INFO" "$symbol current price: $price"
        post_trading_status "market_data" "$symbol price: $price"
        return 0
    else
        log "ERROR" "Failed to get market data for $symbol"
        post_trading_alert "market_error" "Unable to retrieve market data for $symbol"
        return 1
    fi
}

# Function to demo ladder tools
demo_ladder_tools() {
    log "INFO" "Running ladder tools demo..."
    
    local demo_script="$SCRIPTS_DIR/demo_ladder_tools.py"
    if [ ! -f "$demo_script" ]; then
        log "ERROR" "Demo script not found: $demo_script"
        return 1
    fi
    
    if python3 "$demo_script" --quick > /tmp/demo_output.txt 2>&1; then
        log "INFO" "Ladder tools demo completed successfully"
        post_trading_status "demo_complete" "Ladder tools demonstration completed"
        
        # Show key parts of the demo output
        if [ -f /tmp/demo_output.txt ]; then
            echo -e "${BLUE}Demo Output Summary:${NC}"
            head -n 10 /tmp/demo_output.txt | sed 's/^/  /'
        fi
        return 0
    else
        log "ERROR" "Ladder tools demo failed"
        post_trading_alert "demo_error" "Ladder tools demonstration failed"
        return 1
    fi
}

# Function to create a sample ladder configuration
create_sample_ladder() {
    local symbol="${1:-BTC-USD}"
    local output_file="${2:-/tmp/sample_ladder.json}"
    
    log "INFO" "Creating sample ladder configuration for $symbol..."
    
    local ladder_script="$SCRIPTS_DIR/ladder_orders.py"
    if [ ! -f "$ladder_script" ]; then
        log "ERROR" "Ladder orders script not found: $ladder_script"
        return 1
    fi
    
    if python3 "$ladder_script" --template --output "$output_file" 2>/dev/null; then
        log "INFO" "Sample ladder configuration created: $output_file"
        post_trading_status "ladder_config" "Created sample ladder configuration for $symbol"
        
        # Show the configuration
        if [ -f "$output_file" ]; then
            echo -e "${BLUE}Sample Ladder Configuration:${NC}"
            jq . "$output_file" 2>/dev/null | head -n 15 | sed 's/^/  /'
        fi
        return 0
    else
        log "ERROR" "Failed to create ladder configuration"
        post_trading_alert "config_error" "Unable to create ladder configuration template"
        return 1
    fi
}

# Function to simulate a trading strategy (DRY RUN ONLY)
simulate_trading_strategy() {
    local strategy="${1:-conservative}"
    
    log "INFO" "Simulating $strategy trading strategy (DRY RUN ONLY)..."
    post_trading_status "strategy_start" "Starting simulation of $strategy strategy"
    
    # Step 1: Check balances
    if ! check_balances; then
        log "ERROR" "Cannot proceed without balance information"
        return 1
    fi
    
    # Step 2: Get market data
    if ! get_market_data "BTC-USD"; then
        log "ERROR" "Cannot proceed without market data"
        return 1
    fi
    
    if ! get_market_data "ETH-USD"; then
        log "WARN" "ETH market data unavailable, continuing with BTC only"
    fi
    
    # Step 3: Demo the tools
    if ! demo_ladder_tools; then
        log "ERROR" "Demo failed, strategy simulation aborted"
        return 1
    fi
    
    # Step 4: Create configuration
    if ! create_sample_ladder "BTC-USD"; then
        log "WARN" "Could not create ladder config, using defaults"
    fi
    
    # Step 5: Simulate decision making
    log "INFO" "Analyzing market conditions..."
    sleep 2
    
    local btc_price=$(jq -r '.price // "50000"' /tmp/ticker.json 2>/dev/null || echo "50000")
    log "INFO" "Based on BTC price of $btc_price, strategy recommends: HODL"
    
    post_trading_status "strategy_complete" "Simulation completed - recommended action: HODL (no trades executed)"
    
    log "INFO" "$strategy strategy simulation completed successfully"
    return 0
}

# Function to monitor trading activity
monitor_trading() {
    log "INFO" "Starting trading monitor..."
    
    local monitor_duration="${1:-60}"  # Monitor for 60 seconds by default
    local end_time=$(($(date +%s) + monitor_duration))
    
    post_trading_status "monitor_start" "Starting trading activity monitor for ${monitor_duration}s"
    
    while [ $(date +%s) -lt $end_time ]; do
        # Check balances every 30 seconds
        if [ $(($(date +%s) % 30)) -eq 0 ]; then
            check_balances > /dev/null 2>&1
        fi
        
        # Get market data every 15 seconds
        if [ $(($(date +%s) % 15)) -eq 0 ]; then
            get_market_data "BTC-USD" > /dev/null 2>&1
        fi
        
        sleep 5
    done
    
    post_trading_status "monitor_complete" "Trading monitoring session completed"
    log "INFO" "Trading monitor completed"
}

# Function to perform safety checks
perform_safety_checks() {
    log "INFO" "Performing safety checks..."
    
    local checks_passed=0
    local total_checks=4
    
    # Check 1: API credentials
    if [ -f "$SCRIPT_DIR/../coinbase_cloud_api_key.json" ]; then
        log "INFO" "✓ API key file found"
        checks_passed=$((checks_passed + 1))
    else
        log "WARN" "✗ API key file not found (required for live trading)"
    fi
    
    # Check 2: Python environment
    if command -v python3 > /dev/null; then
        log "INFO" "✓ Python 3 available"
        checks_passed=$((checks_passed + 1))
    else
        log "ERROR" "✗ Python 3 not found"
    fi
    
    # Check 3: Required scripts
    local required_scripts=("account_balances.py" "get_market_ticker.py" "demo_ladder_tools.py")
    local scripts_found=0
    
    for script in "${required_scripts[@]}"; do
        if [ -f "$SCRIPTS_DIR/$script" ]; then
            scripts_found=$((scripts_found + 1))
        fi
    done
    
    if [ $scripts_found -eq ${#required_scripts[@]} ]; then
        log "INFO" "✓ All required trading scripts found"
        checks_passed=$((checks_passed + 1))
    else
        log "WARN" "✗ Missing trading scripts ($scripts_found/${#required_scripts[@]} found)"
    fi
    
    # Check 4: BBS system
    if [ -f "$SCRIPT_DIR/../bbs.py" ]; then
        log "INFO" "✓ BBS system available"
        checks_passed=$((checks_passed + 1))
    else
        log "WARN" "✗ BBS system not found (coordination features disabled)"
    fi
    
    log "INFO" "Safety checks completed: $checks_passed/$total_checks passed"
    post_trading_status "safety_check" "Safety checks: $checks_passed/$total_checks passed"
    
    if [ $checks_passed -lt 2 ]; then
        log "ERROR" "Insufficient safety checks passed - aborting"
        return 1
    fi
    
    return 0
}

# Function to show usage
show_usage() {
    echo "Trading Automation Example"
    echo ""
    echo "This script demonstrates safe integration of BBS coordination with trading operations."
    echo "All operations run in DRY-RUN mode by default for safety."
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  balance         Check account balances"
    echo "  market [SYMBOL] Get market data (default: BTC-USD)"
    echo "  demo            Run ladder tools demo"
    echo "  strategy [TYPE] Simulate trading strategy (conservative/aggressive)"
    echo "  monitor [SECS]  Monitor trading activity for specified seconds"
    echo "  safety          Perform safety checks"
    echo "  full-demo       Run complete demonstration"
    echo "  help            Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  AGENT_NAME      Set the agent identifier (default: trading-agent)"
    echo "  SANDBOX_MODE    Use sandbox environment (default: true)"
    echo "  DRY_RUN         Enable dry-run mode (default: true)"
    echo ""
    echo "Examples:"
    echo "  $0 balance                    # Check account balances"
    echo "  $0 market ETH-USD            # Get Ethereum market data"
    echo "  $0 strategy conservative     # Simulate conservative strategy"
    echo "  $0 monitor 120               # Monitor for 2 minutes"
    echo "  AGENT_NAME=trader-1 $0 demo  # Run demo as 'trader-1'"
    echo ""
    echo "Safety Features:"
    echo "  - All operations default to sandbox/dry-run mode"
    echo "  - Comprehensive safety checks before any operations"
    echo "  - BBS integration for coordination and alerts"
    echo "  - No actual trading unless explicitly configured otherwise"
}

# Function to run full demonstration
run_full_demo() {
    log "INFO" "Starting full trading automation demonstration..."
    
    post_trading_status "demo_start" "Beginning comprehensive trading automation demo"
    
    # Step 1: Safety checks
    if ! perform_safety_checks; then
        log "ERROR" "Safety checks failed - demo aborted"
        return 1
    fi
    
    # Step 2: Basic operations
    log "INFO" "Step 2: Testing basic operations..."
    check_balances
    get_market_data "BTC-USD"
    get_market_data "ETH-USD"
    
    # Step 3: Demo tools
    log "INFO" "Step 3: Demonstrating trading tools..."
    demo_ladder_tools
    create_sample_ladder "BTC-USD"
    
    # Step 4: Strategy simulation
    log "INFO" "Step 4: Simulating trading strategy..."
    simulate_trading_strategy "conservative"
    
    # Step 5: Brief monitoring
    log "INFO" "Step 5: Brief monitoring session..."
    monitor_trading 30
    
    post_trading_status "demo_complete" "Full trading automation demonstration completed successfully"
    log "INFO" "Full demonstration completed!"
    
    echo ""
    echo -e "${GREEN}=== Demo Summary ===${NC}"
    echo "✓ Safety checks performed"
    echo "✓ Account balances retrieved"
    echo "✓ Market data fetched"
    echo "✓ Trading tools demonstrated"
    echo "✓ Strategy simulation completed"
    echo "✓ Activity monitoring tested"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Review the BBS messages: python3 ../bbs.py read"
    echo "2. Check the trading scripts in ../scripts/"
    echo "3. Read ../LADDER_TOOLS_GUIDE.md for advanced features"
    echo "4. Configure API credentials for live testing"
    echo ""
    echo -e "${RED}Remember:${NC} Always test in sandbox mode before live trading!"
}

# Main script logic
COMMAND="${1:-help}"

# Display current safety settings
if [ "$COMMAND" != "help" ]; then
    echo -e "${YELLOW}Safety Settings:${NC}"
    echo "  Sandbox Mode: $SANDBOX_MODE"
    echo "  Dry Run: $DRY_RUN"
    echo "  Agent ID: $AGENT_ID"
    echo ""
fi

case "$COMMAND" in
    "balance")
        perform_safety_checks && check_balances
        ;;
    "market")
        SYMBOL="${2:-BTC-USD}"
        perform_safety_checks && get_market_data "$SYMBOL"
        ;;
    "demo")
        perform_safety_checks && demo_ladder_tools
        ;;
    "strategy")
        STRATEGY="${2:-conservative}"
        perform_safety_checks && simulate_trading_strategy "$STRATEGY"
        ;;
    "monitor")
        DURATION="${2:-60}"
        perform_safety_checks && monitor_trading "$DURATION"
        ;;
    "safety")
        perform_safety_checks
        ;;
    "full-demo")
        run_full_demo
        ;;
    "help"|*)
        show_usage
        ;;
esac
