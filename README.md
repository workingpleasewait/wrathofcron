# 🖖 WrathOfCron

**A comprehensive cron job management and monitoring system for Unix/macOS environments.**

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 📦 Repository Split

**This repository was separated from coinbase-trading on July 30, 2025.** 

WrathOfCron is now a standalone cron job management and monitoring system, independent of trading functionality. This split ensures:

- **🎯 Focused Purpose**: Dedicated to cron job management and monitoring
- **🔧 Independent Operation**: No trading dependencies or external API requirements
- **🚀 Simplified Setup**: Pure Python/shell environment with no financial API credentials needed
- **📊 Core Features**: Complete monitoring, alerting, and dashboard functionality

For trading-related functionality, see the separate [coinbase-trading](https://github.com/workingpleasewait/coinbase-trading) repository.

## 🎯 Overview

WrathOfCron is a powerful toolkit for managing, monitoring, and analyzing cron jobs across multiple machines. It combines centralized configuration management with real-time monitoring, alerting, and visual analytics.

### Key Features

- 🚀 **Centralized Management**: Manage cron jobs across multiple machines from a single Git repository
- 📊 **Real-time Monitoring**: Track cron job execution with comprehensive statistics and analytics
- 🔔 **Smart Alerting**: Instant macOS notifications for failed cron jobs
- 📈 **Visual Dashboard**: Web-based dashboard with interactive charts and heatmaps
- 🔄 **Auto-sync**: Automatic synchronization with version control
- 🛡️ **Safety First**: Automatic backups and rollback capabilities

## 🏗️ Architecture

```
wrathofcron/
├── 📋 Management Scripts
│   ├── cron-manager.sh              # Centralized cron job management
│   └── auto-cron-sync.sh           # Auto-sync integration
├── 📊 Monitoring & Analytics
│   ├── cron_collector.py           # Data pipeline for job monitoring
│   ├── cron_collector_manager.sh   # Collector daemon management
│   ├── cron_dash_tui.py           # Terminal-based dashboard
│   └── cron_dash_web.py           # Web-based dashboard
├── ⚙️ Configuration
│   ├── shared-crontab.txt          # Jobs that run on all machines
│   └── cron-jobs/                  # Machine-specific job definitions
└── 📚 Documentation
    ├── CRON_COLLECTOR_GUIDE.md     # Detailed monitoring guide
    ├── CRON_MANAGEMENT.md           # Management system guide
    └── README_cron_dashboard.md     # Web dashboard documentation
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/workingpleasewait/wrathofcron.git
cd wrathofcron

# Make scripts executable
chmod +x *.sh
chmod +x cron_collector_manager.sh
chmod +x cron_collector.py
chmod +x cron_dash_tui.py
```

### 2. Start Monitoring

```bash
# Start the collector daemon for real-time monitoring
./cron_collector_manager.sh start

# Install monitoring as a cron job (auto-start on reboot)
./cron_collector_manager.sh install
```

### 3. Manage Cron Jobs

```bash
# View current status
./cron-manager.sh status

# Install shared and machine-specific cron jobs
./cron-manager.sh install

# View different types of jobs
./cron-manager.sh show           # Shared jobs
./cron-manager.sh show-machine   # Machine-specific jobs
./cron-manager.sh show-current   # Currently active jobs
```

### 4. View Dashboard

```bash
# Terminal dashboard
./cron_dash_tui.py

# Web dashboard (http://localhost:5001)
python cron_dash_web.py
```

## 📊 Monitoring System

### Data Collection
- **Real-time monitoring**: Watches `~/logs/ladder.jsonl` for new cron job entries
- **Incremental processing**: Only processes new entries since last check
- **Structured logging**: JSONL format with timestamps, exit codes, and messages

### Analytics & Alerts
- **Success rate tracking**: 24-hour and 7-day success percentages
- **Failure analysis**: Detailed tracking of failed runs with exit codes
- **Runtime analysis**: Average intervals between cron job executions
- **macOS notifications**: Instant alerts for failed runs with sound

### Example Log Entry
```json
{"ts":"2025-07-29T04:30:00Z","exit":0,"msg":"Monitor started successfully"}
{"ts":"2025-07-29T04:31:00Z","exit":1,"msg":"Connection failed - API timeout"}
```

## 🎛️ Management System

### Shared Jobs (All Machines)
Configure jobs that run on every machine in `shared-crontab.txt`:

```bash
# Daily system updates at 2 AM
0 2 * * * /usr/local/bin/update-system.sh

# Backup important data at midnight
0 0 * * * /usr/local/bin/backup-data.sh
```

### Machine-Specific Jobs
Configure jobs for specific machines in `cron-jobs/HOSTNAME-crontab.txt`:

```bash
# iMac-specific maintenance
0 3 * * 0 /usr/local/bin/maintenance-script.sh

# MacBook Air-specific backup
0 2 * * * /usr/local/bin/backup-script.sh
```

## 📈 Dashboard Features

### Web Dashboard (Port 5001)
- **Plotly Line Charts**: Runtime intervals over time
- **Success Rate Heatmaps**: Visual patterns by hour and day
- **Status Banner**: Color-coded system health indicator
- **Auto-refresh**: Updates every 30 seconds

### Terminal Dashboard
- **Real-time statistics**: Success rates, failure counts, runtime analysis
- **Last failure details**: Most recent error with timestamp and message
- **Database metrics**: Total entries and storage information

## 🔧 Configuration

### Environment Setup
```bash
# Required directories
mkdir -p ~/logs
mkdir -p ~/.cron_dash

# Required packages (auto-installed)
brew install terminal-notifier  # For macOS notifications
pip install flask plotly         # For web dashboard
```

### Custom Paths
Modify these constants in `cron_collector.py` for custom setups:
```python
LADDER_JSONL_PATH = Path.home() / "logs" / "ladder.jsonl"
DB_PATH = Path.home() / ".cron_dash" / "ladder.db"
CHECK_INTERVAL = 30  # seconds
```

## 🔄 Integration Examples

### Adding Logging to Your Scripts

#### Bash Scripts
```bash
#!/bin/bash
# Your cron job script

# ... your logic here ...

# Log the result
EXIT_CODE=$?
SUMMARY="Your operation description"
echo "{\"ts\":\"$(date -Iseconds)\",\"exit\":$EXIT_CODE,\"msg\":\"$SUMMARY\"}" >> ~/logs/ladder.jsonl
```

#### Python Scripts
```python
import json
from datetime import datetime
from pathlib import Path

def log_cron_result(exit_code: int, message: str):
    entry = {
        "ts": datetime.now().isoformat() + "Z",
        "exit": exit_code,
        "msg": message
    }
    
    log_file = Path.home() / "logs" / "ladder.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

# Usage in your Python scripts
try:
    # Your code here
    log_cron_result(0, "Operation completed successfully")
except Exception as e:
    log_cron_result(1, f"Operation failed: {str(e)}")
```

## 🛠️ Available Commands

### Collector Management
```bash
./cron_collector_manager.sh start     # Start daemon
./cron_collector_manager.sh stop      # Stop daemon
./cron_collector_manager.sh status    # Show status and stats
./cron_collector_manager.sh logs      # View recent logs
./cron_collector_manager.sh install   # Install as cron job
```

### Cron Job Management
```bash
./cron-manager.sh status              # Show comprehensive status
./cron-manager.sh install             # Install all cron jobs
./cron-manager.sh sync                # Sync jobs to repository
./cron-manager.sh setup-auto-sync     # Enable auto-sync
```

### Analytics
```bash
python cron_collector.py --stats      # Show current statistics
python cron_collector.py --parse-existing  # Parse existing logs
./cron_dash_tui.py                    # Terminal dashboard
python cron_dash_web.py               # Web dashboard
```

## 🚨 Troubleshooting

### Common Issues

1. **JSONL file not found**
   ```bash
   mkdir -p ~/logs
   touch ~/logs/ladder.jsonl
   ```

2. **Database permissions**
   ```bash
   chmod 644 ~/.cron_dash/ladder.db
   ```

3. **Notifications not working**
   ```bash
   brew install terminal-notifier
   terminal-notifier -title "Test" -message "Hello"
   ```

4. **Web dashboard not loading**
   ```bash
   pip install flask plotly
   python cron_dash_web.py
   ```

### Debug Mode
Enable detailed logging in `cron_collector.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 📋 Examples Directory

The `examples/` directory contains sample implementations:

- `agent_coordination.sh` - Multi-agent coordination patterns
- `cron_bbs_status.sh` - BBS system status monitoring
- `git_commit_bot_workflow.sh` - Automated Git workflows
- `trading_automation.sh` - Trading system automation
- `watch_logs.sh` - Log monitoring examples
- `example_notebook.ipynb` - Jupyter notebook with analysis examples

## 🔒 Security Considerations

- **File Permissions**: Ensure cron files have appropriate permissions (644)
- **Path Validation**: All scripts validate file paths and permissions
- **Process Isolation**: Daemon runs with user permissions, not root
- **Log Rotation**: Automatic log rotation prevents disk space issues

## 📊 Performance

- **Memory Usage**: ~10-20MB for daemon process
- **CPU Impact**: Minimal (checks every 30 seconds)
- **Disk Usage**: SQLite database grows ~1KB per 100 entries
- **Network**: All operations are local (except dashboard access)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit: `git commit -am 'Add feature-name'`
5. Push: `git push origin feature-name`
6. Create a Pull Request

## 📄 License

MIT License - see LICENSE file for details.

## 🎉 Why "WrathOfCron"?

A playful homage to the 1982 film **"Star Trek II: The Wrath of Khan"** – because managing cron jobs shouldn't make you angry! Just as Khan was a formidable adversary who required careful strategy to defeat, unruly cron jobs can wreak havoc on your systems if left unchecked.

This toolkit brings peace and order to the chaotic world of scheduled tasks, turning the "wrath" of broken cron jobs into the "wisdom" of well-monitored automation. Consider WrathOfCron your strategic defense system against the Khan-like chaos of failing scheduled tasks.

---

**Master your cron jobs. Monitor everything. Never miss a failure again.** 🚀

For detailed documentation on specific components:
- [📊 Monitoring System Guide](CRON_COLLECTOR_GUIDE.md)
- [⚙️ Management System Guide](CRON_MANAGEMENT.md)  
- [🌐 Web Dashboard Guide](README_cron_dashboard.md)
