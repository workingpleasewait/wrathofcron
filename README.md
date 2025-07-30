# 🖖 WrathOfCron

**A comprehensive cron job management and monitoring system for Unix/macOS environments.**

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🎯 Overview

WrathOfCron is a powerful toolkit for managing, monitoring, and analyzing cron jobs across multiple machines. It combines centralized configuration management with real-time monitoring, alerting, and visual analytics.

### Key Features

- 🚀 **Centralized Management**: Manage cron jobs across multiple machines from a single Git repository
- 📊 **Real-time Monitoring**: Track cron job execution with comprehensive statistics and analytics
- 🔔 **Smart Alerting**: Instant macOS & Linux notifications for failed cron jobs
- 📈 **Visual Dashboard**: Web-based dashboard with interactive charts and heatmaps
- 🔄 **Auto-sync**: Automatic synchronization with version control
- 🛡️ **Safety First**: Automatic backups and rollback capabilities

## ⚙️ Requirements & Installation

### Dependencies
- **Python 3.7+**
- **Git**
- **Homebrew** (for macOS notifications)

### Installation Steps

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-username/wrathofcron.git
    cd wrathofcron
    ```

2.  **Install Python Packages**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install OS-Specific Notifiers**
    -   **macOS**: `terminal-notifier` is required for notifications.
        ```bash
        brew install terminal-notifier
        ```
    -   **Linux**: `notify-send` is required (usually pre-installed on modern desktops).

4.  **Set Up Directories**
    ```bash
    mkdir -p ~/logs ~/.cron_dash
    ```

## 🚀 Quick Start

1.  **Start the Monitoring Daemon**
    To begin real-time monitoring, start the collector daemon:
    ```bash
    ./cron_collector_manager.sh start
    ```

2.  **Install as a Cron Job**
    To ensure the collector runs on system startup, install it as a cron job:
    ```bash
    ./cron_collector_manager.sh install
    ```

3.  **View the Web Dashboard**
    Access the web dashboard to see real-time analytics:
    ```bash
    python cron_dash_web.py
    # Open http://localhost:5001 in your browser
    ```

## 🛠️ CLI Flags and Commands

### `cron_collector.py`
The core data collection and analysis script.

| Flag                | Description                                                                    |
| ------------------- | ------------------------------------------------------------------------------ |
| `--parse-existing`  | Parses all existing entries in `ladder.jsonl` from the beginning.              |
| `--stats`           | Displays current statistics and exits.                                         |
| `--daemon`          | Runs the collector as a background daemon.                                     |
| `--check-interval N` | Sets the check interval in seconds (Default: 30).                              |
| `--db-path PATH`    | Specifies a custom path for the SQLite database.                               |
| `--log-level LEVEL` | Sets the logging level (e.g., `DEBUG`, `INFO`, `WARNING`).                       |

### `cron_collector_manager.sh`
A helper script to manage the `cron_collector.py` daemon.

| Command   | Description                                                           |
| --------- | --------------------------------------------------------------------- |
| `start`   | Starts the collector daemon.                                          |
| `stop`    | Stops the collector daemon.                                           |
| `status`  | Shows the current status and key statistics.                          |
| `restart` | Restarts the collector daemon.                                        |
| `logs`    | Tails the collector's log file.                                       |
| `parse`   | A shortcut for `cron_collector.py --parse-existing`.                  |
| `install` | Installs a cron job to start the collector on system reboot.          |

### `cron-manager.sh`
Manages the synchronization of cron jobs across machines.

| Command           | Description                                                        |
| ----------------- | ------------------------------------------------------------------ |
| `install`         | Installs shared and machine-specific cron jobs from text files.    |
| `sync`            | Syncs the current crontab to the shared `shared-crontab.txt` file. |
| `show`            | Displays the contents of the shared cron file.                     |
| `show-machine`    | Displays the machine-specific cron jobs for the current host.      |
| `show-current`    | Shows the currently active crontab.                                |
| `status`          | Provides a summary of shared, machine-specific, and active jobs.   |
| `setup-auto-sync` | Creates a script to enable auto-syncing of cron jobs.              |

## 🌐 Web Dashboard & Authentication

The web dashboard provides a visual overview of your cron jobs.

### Environment Variables
You can configure the web dashboard and its authentication settings using these environment variables:

| Variable           | Description                                       | Default     |
| ------------------ | ------------------------------------------------- | ----------- |
| `DEBUG`            | Enables or disables Flask's debug mode.           | `false`     |
| `HOST`             | The host address for the web server.              | `0.0.0.0`   |
| `PORT`             | The port for the web server.                      | `5001`      |
| `AUTH_USERNAME`    | The username for basic authentication.            | `admin`     |
| `AUTH_PASSWORD`    | The password for basic authentication.            | `password`  |

**Example:**
```bash
export AUTH_USERNAME=myuser
export AUTH_PASSWORD=securepassword
python cron_dash_web.py
```

##  daemon Usage

The `cron_collector.py` script is designed to run as a daemon to continuously monitor your cron jobs. The `cron_collector_manager.sh` script handles the daemon lifecycle.

-   **PID File**: The daemon's process ID is stored in `~/.cron_dash/collector.pid`.
-   **Log File**: Daemon logs are written to `~/.cron_dash/collector.log`.
-   **Graceful Shutdown**: The daemon can be stopped gracefully using `./cron_collector_manager.sh stop`, which sends a `SIGTERM` signal.

## ✅ Testing

This project uses `pytest` for testing.

1.  **Install Testing Dependencies**
    ```bash
    pip install pytest
    ```

2.  **Run Tests**
    Execute `pytest` in the root directory:
    ```bash
    pytest
    ```
    The tests cover unit functionality of the `cron_collector.py` script, including parsing, timestamp normalization, and database interactions.

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

## 🤝 Contributing

1.  Fork the repository.
2.  Create a feature branch: `git checkout -b feature-name`
3.  Make your changes and add tests.
4.  Commit your changes: `git commit -am 'Add new feature'`
5.  Push to the branch: `git push origin feature-name`
6.  Submit a pull request.

## 🔄 Project Status & Inventory

**Last Updated:** $(LC_ALL=C date)

### Current State
- Core monitoring and management components are active
- Multiple script modifications in progress
- Testing framework integrated with pytest
- Web dashboard and TUI interfaces available
- Auto-sync functionality implemented

### Active Components
- **Management Scripts**: cron-manager.sh, auto-cron-sync.sh
- **Monitoring**: cron_collector.py, cron_collector_manager.sh
- **Dashboards**: cron_dash_web.py, cron_dash_tui.py
- **Testing**: test_cron_collector.py
- **Configuration**: shared-crontab.txt, .gitignore

### Modified Files (Pending Commit)
- auto-cron-sync.sh
- cron-manager.sh
- cron_collector.py
- cron_collector_manager.sh
- cron_dash_tui.py
- cron_dash_web.py
- requirements.txt

### New Files (Untracked)
- .gitignore
- .last-cron-check
- test_cron_collector.py

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
