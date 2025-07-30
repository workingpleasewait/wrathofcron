#!/bin/bash
# Git Commit Bot Workflow - Sample integration with Bulletin Board Agent
# This script demonstrates how a Git Commit Bot would post commit summaries to the bulletin board

set -e

# Configuration
export AGENT_NAME="GitCommitBot"
export BBS_DATA_DIR="./my_bbs_data"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🤖 Git Commit Bot - Bulletin Board Integration Demo${NC}"
echo "=================================================="

# Function to get latest commit info
get_latest_commit() {
    local sha=$(git log -1 --pretty=format:"%h")
    local message=$(git log -1 --pretty=format:"%s")
    local author=$(git log -1 --pretty=format:"%an")
    local date=$(git log -1 --pretty=format:"%ci")
    
    echo "$sha|$message|$author|$date"
}

# Function to post commit summary to bulletin board
post_commit_summary() {
    local commit_info="$1"
    IFS='|' read -r sha message author date <<< "$commit_info"
    
    local summary="New commit by $author: $message (SHA: $sha)"
    
    echo -e "${YELLOW}📝 Posting commit summary to bulletin board...${NC}"
    python3 bbs.py post --subject "Commit Summary" "$summary"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Commit summary posted successfully${NC}"
    else
        echo -e "${RED}❌ Failed to post commit summary${NC}"
        return 1
    fi
}

# Function to demonstrate reading recent commit messages
read_recent_commits() {
    echo -e "${YELLOW}📖 Reading recent Git Commit Bot messages...${NC}"
    
    # Get messages from the last hour
    local since_time=$(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u -v-1H '+%Y-%m-%dT%H:%M:%SZ')
    
    python3 bbs.py read --since "$since_time" --format json | \
        jq -r '.[] | select(.author == "GitCommitBot") | "[\(.timestamp)] \(.subject): \(.message)"'
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Recent messages retrieved${NC}"
    else
        echo -e "${RED}❌ Failed to retrieve messages${NC}"
    fi
}

# Function to simulate Git Commit Bot monitoring
monitor_commits() {
    echo -e "${YELLOW}🔍 Monitoring for new commits...${NC}"
    echo "In a real implementation, this would:"
    echo "1. Watch for git hooks (post-commit, post-receive)"
    echo "2. Monitor git log changes"
    echo "3. Automatically post summaries for new commits"
    echo
}

# Main workflow demonstration
main() {
    echo -e "${BLUE}Step 1: Check if we're in a git repository${NC}"
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${RED}❌ Not in a git repository. Creating demo scenario...${NC}"
        echo
        echo -e "${YELLOW}Demo Mode: Simulating commit summary${NC}"
        python3 bbs.py post --subject "Commit Summary" "Demo commit: Added Git Commit Bot integration (SHA: abc123f)"
    else
        echo -e "${GREEN}✅ Git repository detected${NC}"
        
        echo
        echo -e "${BLUE}Step 2: Get latest commit information${NC}"
        local commit_info=$(get_latest_commit)
        echo "Latest commit: $commit_info"
        
        echo
        echo -e "${BLUE}Step 3: Post commit summary to bulletin board${NC}"
        post_commit_summary "$commit_info"
    fi
    
    echo
    echo -e "${BLUE}Step 4: Demonstrate reading commit messages${NC}"
    read_recent_commits
    
    echo
    echo -e "${BLUE}Step 5: Show integration with other agents${NC}"
    echo -e "${YELLOW}🔗 Other agents can now read these commit summaries:${NC}"
    echo
    echo "# Bulletin Board Agent reading Git Commit Bot messages:"
    echo "export AGENT_NAME=\"BulletinBoardAgent\""
    echo "python3 bbs.py read --format json | jq '.[] | select(.author == \"GitCommitBot\")'"
    echo
    echo "# Trading Collector responding to code changes:"
    echo "export AGENT_NAME=\"TradingCollector\""
    echo "python3 bbs.py post --subject \"System Update\" \"Detected code changes, restarting trading algorithms\""
    
    echo
    echo -e "${BLUE}Step 6: Monitor mode simulation${NC}"
    monitor_commits
    
    echo
    echo -e "${GREEN}🎉 Git Commit Bot workflow demonstration complete!${NC}"
    echo
    echo -e "${BLUE}Summary of integration benefits:${NC}"
    echo "• Automatic commit notifications"
    echo "• Centralized development activity logging"
    echo "• Inter-agent coordination on code changes"
    echo "• Structured message format for easy processing"
    echo "• Historical commit tracking via bulletin board"
}

# Run the main workflow
main "$@"
