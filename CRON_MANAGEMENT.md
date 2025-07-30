# Centralized Cron Job Management

## 🎯 Overview
This system allows you to manage cron jobs across multiple machines from a single Git repository. It supports both shared cron jobs (run on all machines) and machine-specific cron jobs (run only on specific machines).

## 📁 File Structure
```
cron-manager.sh              # Main management script
shared-crontab.txt           # Shared cron jobs (synced to all machines)
cron-jobs/                   # Machine-specific cron jobs directory
├── imac-crontab.txt        # Jobs specific to iMac
├── macbook-air-crontab.txt # Jobs specific to MacBook Air
└── server-crontab.txt      # Jobs specific to server
auto-cron-sync.sh           # Auto-sync integration script
cron-sync.log               # Activity log
```

## 🚀 Quick Start

### 1. Check Current Status
```bash
./cron-manager.sh status
```

### 2. Install Cron Jobs
```bash
# Install both shared and machine-specific jobs
./cron-manager.sh install
```

### 3. View Different Types of Jobs
```bash
# Show shared jobs (run on all machines)
./cron-manager.sh show

# Show machine-specific jobs (this machine only)
./cron-manager.sh show-machine

# Show currently active jobs
./cron-manager.sh show-current
```

## 📋 Available Commands

| Command | Description |
|---------|-------------|
| `status` | Show comprehensive status of cron management |
| `install` | Install shared + machine-specific cron jobs |
| `sync` | Sync current cron jobs to shared repository |
| `show` | Show shared cron jobs |
| `show-machine` | Show machine-specific cron jobs |
| `show-current` | Show currently active cron jobs |
| `setup-auto-sync` | Set up automatic syncing with warp system |

## 🔧 Configuration

### Shared Cron Jobs
Edit `shared-crontab.txt` to add jobs that run on all machines:
```bash
# Every day at midnight
0 0 * * * /path/to/daily-task.sh

# Every hour  
0 * * * * /path/to/hourly-task.sh
```

### Machine-Specific Cron Jobs
Edit `cron-jobs/HOSTNAME-crontab.txt` for machine-specific jobs:
```bash
# iMac-specific maintenance
0 3 * * 0 /usr/local/bin/maintenance-script.sh

# MacBook Air-specific backup
0 2 * * * /usr/local/bin/backup-script.sh
```

## 🔄 Multi-Machine Workflow

### Setting Up on Primary Machine
1. **Configure jobs**: Edit `shared-crontab.txt` and machine-specific files
2. **Install locally**: `./cron-manager.sh install`
3. **Sync to repository**: `./cron-manager.sh sync`

### Setting Up on Secondary Machines
1. **Pull latest**: `git pull`
2. **Install jobs**: `./cron-manager.sh install`
3. **Verify**: `./cron-manager.sh status`

## 🤖 Auto-Sync Integration

The system integrates with the `warp.sync-with-readme` system:

1. **Enable auto-sync**: `./cron-manager.sh setup-auto-sync`
2. **Automatic detection**: Changes to cron files trigger auto-installation
3. **Cross-machine sync**: Jobs sync automatically via Git

## 🛡️ Safety Features

- **Automatic backups**: Existing crontabs backed up before changes
- **Dry-run preview**: Review jobs before installation
- **Machine isolation**: Machine-specific jobs only run on intended machines
- **Version control**: All changes tracked in Git
- **Rollback capability**: Easy to revert to previous configurations

## 📊 Example Setup

### Shared Jobs (All Machines)
```bash
# Daily system updates at 2 AM
0 2 * * * /usr/local/bin/update-system.sh

# Backup important data at midnight
0 0 * * * /usr/local/bin/backup-data.sh

# Clean temp files every 6 hours
0 */6 * * * find /tmp -type f -mtime +1 -delete
```

### iMac-Specific Jobs
```bash
# Restart network service weekly
0 3 * * 0 /usr/local/bin/restart-network.sh

# Update Homebrew packages
0 6 * * 1 /usr/local/bin/brew update && /usr/local/bin/brew upgrade
```

### MacBook Air-Specific Jobs  
```bash
# Battery optimization script
0 8 * * * /usr/local/bin/optimize-battery.sh

# Sync work documents
0 18 * * 1-5 /usr/local/bin/sync-work-docs.sh
```

## 🔍 Troubleshooting

### Check Logs
```bash
# View sync activity
cat cron-sync.log

# Check cron system logs
tail -f /var/log/cron
```

### Verify Installation
```bash
# Check what's actually installed
crontab -l

# Verify file permissions
ls -la cron-jobs/
```

### Reset if Needed
```bash
# Backup current setup
cp shared-crontab.txt shared-crontab.backup.txt

# Reinstall fresh
./cron-manager.sh install
```

## ✅ Benefits

1. **Centralized Management**: Single source for all scheduled tasks
2. **Cross-Machine Sync**: Same workflow on all your devices  
3. **Machine Flexibility**: Different jobs for different machines
4. **Version Control**: Track all changes with Git
5. **Automatic Sync**: Integrates with existing sync system
6. **Safety First**: Backups and rollback capabilities

---

**Perfect for multi-Mac development workflows!** 🚀
