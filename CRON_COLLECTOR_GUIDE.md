# Cron Collector Data Pipeline

A comprehensive data pipeline for monitoring, analyzing, and alerting on cron job execution data from `ladder.jsonl`.

## 🎯 Overview

The Cron Collector watches `~/logs/ladder.jsonl` for new entries, stores them in a lightweight SQLite database, computes aggregates like success rates and average runtime, and sends macOS notifications for any run with `exit != 0`.

## 📁 File Structure

```
cron_collector.py              # Main data pipeline script
cron_collector_manager.sh      # Management script for start/stop/status
~/.cron_dash/
├── ladder.db                  # SQLite database
├── collector.log              # Main collector logs
├── daemon.log                 # Daemon mode logs
└── collector.pid              # Process ID file
~/logs/ladder.jsonl            # Input data file (JSONL format)
```

## 🚀 Quick Start

### 1. Basic Usage
```bash
# Parse existing entries
python3 cron_collector.py --parse-existing

# Show current statistics
python3 cron_collector.py --stats

# Start watching for new entries
python3 cron_collector.py
```

### 2. Using the Management Script
```bash
# Start the collector daemon
./cron_collector_manager.sh start

# Check status and show stats
./cron_collector_manager.sh status

# Stop the daemon
./cron_collector_manager.sh stop

# Install as cron job (auto-start on reboot)
./cron_collector_manager.sh install
```

## 📊 Features

### Data Collection
- **Real-time monitoring**: Watches `ladder.jsonl` for new entries every 30 seconds
- **Incremental processing**: Only processes new lines since last check
- **Duplicate prevention**: Avoids processing the same entry multiple times
- **Error handling**: Graceful handling of malformed JSON or missing files

### Data Storage
- **SQLite database**: Lightweight, serverless database at `~/.cron_dash/ladder.db`
- **Indexed tables**: Optimized queries with proper indexes
- **Structured schema**: Clean separation of raw data and computed statistics

### Analytics & Aggregates
- **Success rate**: Percentage of successful runs (exit code 0) in last 24h and 7 days
- **Failure tracking**: Count and details of failed runs
- **Runtime analysis**: Average interval between cron job executions
- **Historical data**: Complete record of all cron job executions

### Alerting
- **macOS notifications**: Instant alerts for failed runs using `terminal-notifier`
- **Failure details**: Notifications include exit code and error message
- **Sound alerts**: Different sounds for different types of failures
- **Auto-install**: Automatically installs `terminal-notifier` if missing

## 📋 Input Data Format

The collector expects JSONL format entries in `~/logs/ladder.jsonl`:

```json
{"ts":"2025-07-29T04:30:00Z","exit":0,"msg":"Monitor started successfully"}
{"ts":"2025-07-29T04:31:00Z","exit":1,"msg":"Connection failed - API timeout"}
{"ts":"2025-07-29T04:32:00Z","exit":0,"msg":"Order check completed - 3 orders tracked"}
```

### Required Fields
- `ts`: ISO 8601 timestamp
- `exit`: Exit code (0 for success, non-zero for failure)  
- `msg`: Human-readable message describing the operation

## 🛠️ Command Line Options

### Main Script (`cron_collector.py`)

```bash
python3 cron_collector.py [OPTIONS]

Options:
  --parse-existing     Parse all existing entries from JSONL file
  --stats              Display current statistics and exit
  --daemon             Run as background daemon
  --check-interval N   Check interval in seconds (default: 30)
```

### Management Script (`cron_collector_manager.sh`)

```bash
./cron_collector_manager.sh {start|stop|status|restart|logs|parse|stats|install}

Commands:
  start     - Start the collector daemon
  stop      - Stop the collector daemon  
  status    - Check daemon status and show stats
  restart   - Restart the collector daemon
  logs      - Show recent collector logs
  parse     - Parse existing entries from ladder.jsonl
  stats     - Show current statistics
  install   - Install as cron job (auto-start on reboot)
```

## 📈 Statistics Dashboard

The collector computes and displays comprehensive statistics:

```
============================================================
📊 CRON COLLECTOR STATISTICS
============================================================

📈 Last 24 Hours:
   Total runs: 5
   Success rate: 60.0%
   Failed runs: 2

📊 Last 7 Days:
   Total runs: 5
   Success rate: 60.0%

⏱️  Average interval: 1.0 minutes

🚨 Last failure:
   Time: 2025-07-29T04:33:00Z
   Message: Authentication failed - invalid credentials...

💾 Database: 5 total entries
============================================================
```

### Computed Metrics

- **Total runs**: Count of cron job executions in time period
- **Success rate**: Percentage of runs with exit code 0
- **Failed runs**: Count of runs with non-zero exit codes
- **Average interval**: Time between consecutive cron job runs
- **Last failure**: Most recent failure timestamp and message
- **Database size**: Total number of entries stored

## 🔧 Database Schema

### cron_entries Table
```sql
CREATE TABLE cron_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    message TEXT NOT NULL,
    parsed_at TEXT NOT NULL,
    UNIQUE(timestamp, exit_code, message)
);
```

### stats_cache Table
```sql
CREATE TABLE stats_cache (
    metric TEXT PRIMARY KEY,
    value REAL NOT NULL,
    computed_at TEXT NOT NULL
);
```

## 🚨 Notification System

### macOS Integration
- Uses `terminal-notifier` for native macOS notifications
- Auto-installs via Homebrew if not present
- Customizable sounds and message formatting

### Notification Triggers
- **Any non-zero exit code**: Triggers immediate notification
- **Sound differentiation**: Different sounds for different error types
- **Message formatting**: Includes exit code and truncated error message

### Example Notification
```
Title: 🚨 Cron Job Failed
Message: Exit code 2: Authentication failed - invalid credentials
Sound: Basso
```

## ⚙️ Configuration

### Environment Variables
The collector uses sensible defaults but can be customized:

```bash
# In cron_collector.py
LADDER_JSONL_PATH = Path.home() / "logs" / "ladder.jsonl"
DB_PATH = Path.home() / ".cron_dash" / "ladder.db"
CHECK_INTERVAL = 30  # seconds
STATS_INTERVAL = 300  # 5 minutes for stats computation
```

### Customization
To modify paths or intervals, edit the constants at the top of `cron_collector.py`.

## 🔄 Integration with Existing Cron Jobs

### Ladder Monitor Integration
The collector is designed to work with the existing ladder monitoring system:

```bash
# In monitor_ladder.sh (example)
SUMMARY="Monitor started successfully"
echo "{\"ts\":\"$(date -Iseconds)\",\"exit\":$?,\"msg\":\"$SUMMARY\"}" >> ~/logs/ladder.jsonl
```

### Adding to Other Scripts
To integrate with other cron jobs, add similar logging:

```bash
#!/bin/bash
# Your cron job script

# ... your logic here ...

# Log the result
EXIT_CODE=$?
SUMMARY="Your operation description"
echo "{\"ts\":\"$(date -Iseconds)\",\"exit\":$EXIT_CODE,\"msg\":\"$SUMMARY\"}" >> ~/logs/ladder.jsonl
```

## 🛡️ Production Deployment

### Daemon Mode
The collector supports daemon mode for production deployment:

```bash
# Start as daemon
./cron_collector_manager.sh start

# Install as cron job (auto-start on reboot)
./cron_collector_manager.sh install
```

### Process Management
- **PID file**: Prevents multiple instances
- **Signal handling**: Graceful shutdown on SIGINT/SIGTERM
- **Log rotation**: Separate log files for daemon and interactive modes
- **Error recovery**: Continues operation despite temporary failures

### Monitoring the Monitor
The collector itself logs its operations:

```bash
# Check collector logs
./cron_collector_manager.sh logs

# Check collector status
./cron_collector_manager.sh status
```

## 🔍 Troubleshooting

### Common Issues

1. **JSONL file not found**
   ```bash
   # Create the logs directory
   mkdir -p ~/logs
   
   # Check file permissions
   ls -la ~/logs/ladder.jsonl
   ```

2. **Database permissions**
   ```bash
   # Check database directory
   ls -la ~/.cron_dash/
   
   # Reset permissions if needed
   chmod 644 ~/.cron_dash/ladder.db
   ```

3. **terminal-notifier not working**
   ```bash
   # Install manually if auto-install fails
   brew install terminal-notifier
   
   # Test notifications
   terminal-notifier -title "Test" -message "Hello"
   ```

4. **Daemon not starting**
   ```bash
   # Check logs for errors
   ./cron_collector_manager.sh logs
   
   # Try running interactively first
   python3 cron_collector.py
   ```

### Debug Mode
Enable debug logging by modifying the logging level in `cron_collector.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    # ... rest of config
)
```

## 📈 Performance Considerations

### Resource Usage
- **Memory**: Minimal (~10-20MB for daemon process)
- **CPU**: Very low (checks every 30 seconds)
- **Disk**: SQLite database grows slowly (~1KB per 100 entries)
- **Network**: None (all local operations)

### Scalability
- **File size**: Handles large JSONL files efficiently with incremental processing
- **Database size**: SQLite handles millions of entries without issues
- **Check frequency**: Configurable interval balances responsiveness vs. resource usage

## 🔗 Integration Examples

### With Existing Ladder Tools
```bash
# In your existing cron jobs, add logging:
echo "{\"ts\":\"$(date -Iseconds)\",\"exit\":$?,\"msg\":\"Ladder check completed\"}" >> ~/logs/ladder.jsonl
```

### With Custom Scripts
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

## 📚 Next Steps

1. **Start the collector**: `./cron_collector_manager.sh start`
2. **Install for auto-start**: `./cron_collector_manager.sh install`
3. **Monitor your cron jobs**: Check `./cron_collector_manager.sh status`
4. **Integrate with existing scripts**: Add JSONL logging to your cron jobs
5. **Customize as needed**: Modify intervals, paths, or notification settings

---

**The Cron Collector provides comprehensive monitoring and alerting for your cron job ecosystem!** 🚀
