#!/bin/bash

# Enable strict error handling
set -euo pipefail

# Centralized Cron Job Manager
# Syncs cron jobs across multiple machines via Git
# Integrated with warp.sync-with-readme system

CRON_FILE="shared-crontab.txt"
MACHINE_SPECIFIC_DIR="cron-jobs"
# Support MACHINE_NAME_OVERRIDE environment variable
MACHINE_NAME="${MACHINE_NAME_OVERRIDE:-$(hostname -s)}"
BACKUP_FILE="crontab-backup-$(LC_ALL=C date +%Y%m%d-%H%M%S).txt"
LOG_FILE="cron-sync.log"
TMPFILE=""

# Ensure temp file cleanup on exit
trap 'rm -f "$TMPFILE"' EXIT

# Logging function
log() {
    echo "[$(LC_ALL=C date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

create_machine_specific_dir() {
    mkdir -p "$MACHINE_SPECIFIC_DIR"
    log "Created machine-specific directory: $MACHINE_SPECIFIC_DIR"
}

install_shared_cron() {
    log "Installing shared cron jobs on $MACHINE_NAME..."
    create_machine_specific_dir
    
    # Backup existing crontab
    if crontab -l 2>/dev/null > /dev/null; then
        crontab -l > "$BACKUP_FILE"
        log "Backed up existing crontab to $BACKUP_FILE"
    fi
    
    # Combine shared and machine-specific cron jobs
    TMPFILE=$(mktemp)
    > "$TMPFILE"  # Clear temp file
    
    # Add shared cront jobs
    if [ -f "$CRON_FILE" ]; then
        log "Adding shared cron jobs from $CRON_FILE"
        echo "# === SHARED CRON JOBS (synced across all machines) ===" >> "$TMPFILE"
        cat "$CRON_FILE" >> "$TMPFILE"
        echo "" >> "$TMPFILE"
    fi
    
    # Add machine-specific cron jobs
    MACHINE_CRON="$MACHINE_SPECIFIC_DIR/$MACHINE_NAME-crontab.txt"
    if [ -f "$MACHINE_CRON" ]; then
        log "Adding machine-specific cron jobs from $MACHINE_CRON"
        echo "# === MACHINE-SPECIFIC CRON JOBS ($MACHINE_NAME only) ===" >> "$TMPFILE"
        cat "$MACHINE_CRON" >> "$TMPFILE"
    fi
    
    # Install combined crontab
    if [ -s "$TMPFILE" ]; then
        crontab "$TMPFILE"
        log "✅ Installed combined cron jobs (shared + machine-specific)"
        echo "📊 Active cron jobs:"
        crontab -l
    else
        log "❌ No cron jobs to install"
    fi
}

sync_cron_from_current() {
    echo "📤 Syncing current cron jobs to shared file..."
    
    if crontab -l 2>/dev/null > /dev/null; then
        crontab -l > "$CRON_FILE"
        echo "✅ Current cron jobs saved to $CRON_FILE"
        
        # Add to git and commit
        git add "$CRON_FILE"
        git commit -m "Update shared cron jobs - $(LC_ALL=C date '+%Y-%m-%d %H:%M:%S')"
        git push
        echo "✅ Cron jobs pushed to repository"
    else
        echo "❌ No cron jobs to sync"
    fi
}

show_shared_cron() {
    echo "📋 Shared cron jobs:"
    if [ -f "$CRON_FILE" ]; then
        cat "$CRON_FILE"
    else
        echo "❌ No shared cron file found"
    fi
}

show_machine_cron() {
    MACHINE_CRON="$MACHINE_SPECIFIC_DIR/$MACHINE_NAME-crontab.txt"
    echo "📋 Machine-specific cron jobs for $MACHINE_NAME:"
    if [ -f "$MACHINE_CRON" ]; then
        cat "$MACHINE_CRON"
    else
        echo "❌ No machine-specific cron file found: $MACHINE_CRON"
    fi
}

show_current_cron() {
    echo "📊 Currently active cron jobs:"
    if crontab -l 2>/dev/null > /dev/null; then
        crontab -l
    else
        echo "❌ No active cron jobs"
    fi
}

auto_sync_setup() {
    log "Setting up auto-sync for cron jobs with warp.sync-with-readme"
    
    # Create auto-sync script
    cat > "auto-cron-sync.sh" << 'EOF'
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
EOF
    
    chmod +x "auto-cron-sync.sh"
    log "✅ Auto-sync script created: auto-cron-sync.sh"
}

status() {
    echo "📊 Centralized Cron Management Status"
    echo "═══════════════════════════════════"
    echo "🖥️  Machine: $MACHINE_NAME"
    echo "📁 Shared cron file: $CRON_FILE"
    echo "📁 Machine-specific dir: $MACHINE_SPECIFIC_DIR"
    echo ""
    
    if [ -f "$CRON_FILE" ]; then
        SHARED_COUNT=$(grep -v '^#' "$CRON_FILE" | grep -v '^$' | wc -l | tr -d ' ')
        echo "📋 Shared cron jobs: $SHARED_COUNT"
    else
        echo "📋 Shared cron jobs: 0 (no file)"
    fi
    
    MACHINE_CRON="$MACHINE_SPECIFIC_DIR/$MACHINE_NAME-crontab.txt"
    if [ -f "$MACHINE_CRON" ]; then
        MACHINE_COUNT=$(grep -v '^#' "$MACHINE_CRON" | grep -v '^$' | wc -l | tr -d ' ')
        echo "🖥️  Machine-specific jobs: $MACHINE_COUNT"
    else
        echo "🖥️  Machine-specific jobs: 0 (no file)"
    fi
    
    if crontab -l 2>/dev/null > /dev/null; then
        ACTIVE_COUNT=$(crontab -l | grep -v '^#' | grep -v '^$' | wc -l | tr -d ' ')
        echo "⚡ Active cron jobs: $ACTIVE_COUNT"
    else
        echo "⚡ Active cron jobs: 0"
    fi
}

case "$1" in
    install)
        install_shared_cron
        ;;
    sync)
        sync_cron_from_current
        ;;
    show)
        show_shared_cron
        ;;
    show-machine)
        show_machine_cron
        ;;
    show-current)
        show_current_cron
        ;;
    status)
        status
        ;;
    setup-auto-sync)
        auto_sync_setup
        ;;
    *)
        echo "Centralized Cron Job Manager"
        echo "Usage: $0 {install|sync|show|show-machine|show-current|status|setup-auto-sync}"
        echo ""
        echo "Commands:"
        echo "  install        - Install shared + machine-specific cron jobs"
        echo "  sync           - Sync current cron jobs to shared repository"
        echo "  show           - Show shared cron jobs"
        echo "  show-machine   - Show machine-specific cron jobs"
        echo "  show-current   - Show currently active cron jobs"
        echo "  status         - Show comprehensive status"
        echo "  setup-auto-sync - Set up automatic syncing"
        echo ""
        echo "Workflow:"
        echo "  1. Set up shared jobs: edit $CRON_FILE"
        echo "  2. Set up machine jobs: edit $MACHINE_SPECIFIC_DIR/\$HOSTNAME-crontab.txt"
        echo "  3. Install: $0 install"
        echo "  4. Sync to other machines: $0 sync"
        echo "  5. On other machines: git pull && $0 install"
        ;;
esac
