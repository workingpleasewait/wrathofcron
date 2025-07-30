#!/usr/bin/env python3
"""
Cron Collector Data Pipeline

Watches ladder.jsonl for new lines, stores entries in SQLite DB,
computes aggregates, and raises terminal-notifier alerts on failures.

Usage:
    python3 cron_collector.py                    # Watch mode (default)
    python3 cron_collector.py --parse-existing   # Parse existing entries
    python3 cron_collector.py --stats            # Show statistics
    python3 cron_collector.py --daemon           # Run as daemon
"""

import argparse
import json
import sqlite3
import sys
import time
import os
import subprocess
import platform
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import signal
import threading
from dateutil import parser as dateutil_parser
import daemon
from daemon import pidfile

# Configuration
LADDER_JSONL_PATH = Path.home() / "logs" / "ladder.jsonl"
DB_PATH = Path.home() / ".cron_dash" / "ladder.db"
CHECK_INTERVAL = 30  # seconds
STATS_INTERVAL = 300  # 5 minutes for stats computation

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / ".cron_dash" / "collector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CronCollector:
    """Data pipeline for collecting and analyzing cron job execution data."""
    
    def __init__(self, db_path: Optional[Path] = None, log_level: str = "INFO"):
        self.db_path = db_path or DB_PATH
        self.jsonl_path = LADDER_JSONL_PATH
        self.last_pos_file = Path.home() / ".cron_dash" / "last_pos"
        self.pid_file_path = Path.home() / ".cron_dash" / "cron_collector.pid"
        self.running = False
        
        # Set up logging
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f'Invalid log level: {log_level}')
        logger.setLevel(numeric_level)
        
        self.init_database()
        self.load_last_position()
        
    def load_last_position(self):
        """Load the last read position from file."""
        try:
            if self.last_pos_file.exists():
                with open(self.last_pos_file, 'r') as f:
                    self.last_position = int(f.read().strip())
                logger.debug(f"Loaded last position: {self.last_position}")
            else:
                self.last_position = 0
                logger.debug("No last position file found, starting from beginning")
        except Exception as e:
            logger.warning(f"Failed to load last position: {e}, starting from 0")
            self.last_position = 0
            
    def save_last_position(self):
        """Save the current read position to file."""
        try:
            self.last_pos_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.last_pos_file, 'w') as f:
                f.write(str(self.last_position))
            logger.debug(f"Saved last position: {self.last_position}")
        except Exception as e:
            logger.error(f"Failed to save last position: {e}")
            
    def normalize_timestamp(self, timestamp: str) -> str:
        """Convert timestamp to UTC ISO-8601 format."""
        try:
            # Parse the timestamp using dateutil which handles various formats
            dt = dateutil_parser.isoparse(timestamp)
            
            # Convert to UTC if timezone aware, otherwise assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
                
            # Return as ISO-8601 string
            return dt.isoformat()
        except Exception as e:
            logger.warning(f"Failed to normalize timestamp '{timestamp}': {e}")
            return timestamp  # Return original if parsing fails
            
    def send_os_notification(self, title: str, message: str, sound: str = "default"):
        """Send OS-specific notification."""
        system = platform.system().lower()
        
        try:
            if system == "darwin":  # macOS
                self._send_macos_notification(title, message, sound)
            elif system == "linux":
                self._send_linux_notification(title, message)
            else:
                logger.warning(f"Notifications not supported on {system}")
                logger.info(f"NOTIFICATION: {title} - {message}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            logger.info(f"FALLBACK NOTIFICATION: {title} - {message}")
            
    def _send_macos_notification(self, title: str, message: str, sound: str = "default"):
        """Send macOS notification using terminal-notifier."""
        # Check if terminal-notifier is available
        result = subprocess.run(
            ["which", "terminal-notifier"], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            error_msg = "terminal-notifier not found. Install with: brew install terminal-notifier"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        # Send notification
        cmd = [
            "terminal-notifier",
            "-title", title,
            "-message", message,
            "-sound", sound
        ]
        
        subprocess.run(cmd, check=True)
        logger.info(f"macOS notification sent: {title} - {message}")
        
    def _send_linux_notification(self, title: str, message: str):
        """Send Linux notification using notify-send."""
        # Check if notify-send is available
        result = subprocess.run(
            ["which", "notify-send"], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            logger.warning("notify-send not found, falling back to logger")
            logger.info(f"NOTIFICATION: {title} - {message}")
            return
            
        # Send notification
        cmd = ["notify-send", title, message]
        subprocess.run(cmd, check=True)
        logger.info(f"Linux notification sent: {title} - {message}")
        
    def stream_parse_jsonl(self, file_path: Path) -> int:
        """Stream-parse JSONL file using lazy line reading."""
        entries_processed = 0
        
        try:
            with open(file_path, 'r') as f:
                # Seek to last known position
                f.seek(self.last_position)
                
                # Process lines one by one (lazy reading)
                for line in f:
                    entry = self.parse_jsonl_line(line)
                    if entry:
                        # Normalize timestamp to UTC ISO-8601
                        entry['timestamp'] = self.normalize_timestamp(entry['timestamp'])
                        
                        if self.insert_entry_safe(entry):
                            entries_processed += 1
                            
                            # Send notification for failures
                            if entry['exit_code'] != 0:
                                self.send_os_notification(
                                    "🚨 Cron Job Failed",
                                    f"Exit code {entry['exit_code']}: {entry['message'][:100]}",
                                    "Basso"
                                )
                    
                # Update and save position
                self.last_position = f.tell()
                self.save_last_position()
                
        except Exception as e:
            logger.error(f"Failed to stream parse JSONL: {e}")
            
        return entries_processed
        
    def create_pid_file(self):
        """Create PID file for daemon process."""
        try:
            self.pid_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.pid_file_path, 'w') as f:
                f.write(str(os.getpid()))
            logger.info(f"PID file created: {self.pid_file_path}")
        except Exception as e:
            logger.error(f"Failed to create PID file: {e}")
            
    def remove_pid_file(self):
        """Remove PID file."""
        try:
            if self.pid_file_path.exists():
                self.pid_file_path.unlink()
                logger.info(f"PID file removed: {self.pid_file_path}")
        except Exception as e:
            logger.error(f"Failed to remove PID file: {e}")
        
    def init_database(self):
        """Initialize SQLite database with required tables."""
        try:
            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cron_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        exit_code INTEGER NOT NULL,
                        message TEXT NOT NULL,
                        parsed_at TEXT NOT NULL,
                        UNIQUE(timestamp, exit_code, message)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS stats_cache (
                        metric TEXT PRIMARY KEY,
                        value REAL NOT NULL,
                        computed_at TEXT NOT NULL
                    )
                """)
                
                # Create indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON cron_entries(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_exit_code ON cron_entries(exit_code)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_parsed_at ON cron_entries(parsed_at)")
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
            
    def parse_jsonl_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single JSONL line into structured data."""
        try:
            line = line.strip()
            if not line:
                return None
                
            data = json.loads(line)
            
            # Validate required fields
            if not all(key in data for key in ['ts', 'exit', 'msg']):
                logger.warning(f"Invalid entry missing required fields: {line}")
                return None
                
            return {
                'timestamp': data['ts'],
                'exit_code': int(data['exit']),
                'message': data['msg'],
                'parsed_at': datetime.now().isoformat()
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON line: {line} - {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing line: {line} - {e}")
            return None
            
    def insert_entry(self, entry: Dict) -> bool:
        """Insert entry into database, avoiding duplicates."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO cron_entries 
                    (timestamp, exit_code, message, parsed_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    entry['timestamp'],
                    entry['exit_code'], 
                    entry['message'],
                    entry['parsed_at']
                ))
                
                if conn.total_changes > 0:
                    logger.debug(f"Inserted new entry: {entry['message'][:50]}...")
                    return True
                else:
                    logger.debug(f"Duplicate entry skipped: {entry['message'][:50]}...")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to insert entry: {e}")
            return False
            
    def insert_entry_safe(self, entry: Dict[str, Any]) -> bool:
        """Insert entry into database with explicit IntegrityError handling."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO cron_entries 
                    (timestamp, exit_code, message, parsed_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    entry['timestamp'],
                    entry['exit_code'], 
                    entry['message'],
                    entry['parsed_at']
                ))
                
                conn.commit()
                logger.debug(f"Inserted new entry: {entry['message'][:50]}...")
                return True
                
        except sqlite3.IntegrityError as e:
            logger.debug(f"Duplicate entry skipped (IntegrityError): {entry['message'][:50]}... - {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to insert entry: {e}")
            return False
            
    def send_notification(self, title: str, message: str, sound: str = "default"):
        """Send macOS notification using terminal-notifier."""
        try:
            # Check if terminal-notifier is available
            result = subprocess.run(
                ["which", "terminal-notifier"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                logger.warning("terminal-notifier not found, installing via Homebrew...")
                subprocess.run(["brew", "install", "terminal-notifier"], check=True)
                
            # Send notification
            cmd = [
                "terminal-notifier",
                "-title", title,
                "-message", message,
                "-sound", sound
            ]
            
            subprocess.run(cmd, check=True)
            logger.info(f"Notification sent: {title} - {message}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to send notification: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending notification: {e}")
            
    def process_new_entries(self) -> int:
        """Process new entries from JSONL file."""
        if not self.jsonl_path.exists():
            logger.debug(f"JSONL file not found: {self.jsonl_path}")
            return 0
            
        try:
            with open(self.jsonl_path, 'r') as f:
                # Seek to last known position
                f.seek(self.last_position)
                new_lines = f.readlines()
                
                # Update position
                self.last_position = f.tell()
                
            entries_processed = 0
            for line in new_lines:
                entry = self.parse_jsonl_line(line)
                if entry:
                    if self.insert_entry(entry):
                        entries_processed += 1
                        
                        # Send notification for failures
                        if entry['exit_code'] != 0:
                            self.send_notification(
                                "🚨 Cron Job Failed",
                                f"Exit code {entry['exit_code']}: {entry['message'][:100]}",
                                "Basso"
                            )
                            
            if entries_processed > 0:
                logger.info(f"Processed {entries_processed} new entries")
                
            return entries_processed
            
        except Exception as e:
            logger.error(f"Failed to process new entries: {e}")
            return 0
            
    def parse_existing_entries(self) -> int:
        """Parse all existing entries from JSONL file using stream parsing."""
        if not self.jsonl_path.exists():
            logger.warning(f"JSONL file not found: {self.jsonl_path}")
            return 0
            
        try:
            # Reset position to start from beginning
            self.last_position = 0
            
            # Use stream parsing for lazy line reading
            entries_processed = 0
            with open(self.jsonl_path, 'r') as f:
                for line in f:
                    entry = self.parse_jsonl_line(line)
                    if entry:
                        # Normalize timestamp to UTC ISO-8601
                        entry['timestamp'] = self.normalize_timestamp(entry['timestamp'])
                        
                        if self.insert_entry_safe(entry):
                            entries_processed += 1
                            
            logger.info(f"Parsed {entries_processed} existing entries")
            
            # Update position to end of file for future watching
            with open(self.jsonl_path, 'r') as f:
                f.seek(0, 2)  # Seek to end
                self.last_position = f.tell()
                self.save_last_position()
                
            return entries_processed
            
        except Exception as e:
            logger.error(f"Failed to parse existing entries: {e}")
            return 0
            
    def compute_stats(self) -> Dict:
        """Compute and cache aggregate statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get time boundaries
                now = datetime.now()
                day_ago = (now - timedelta(days=1)).isoformat()
                week_ago = (now - timedelta(days=7)).isoformat()
                
                stats = {}
                
                # Success rate in last 24h
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END) as success
                    FROM cron_entries 
                    WHERE timestamp >= ?
                """, (day_ago,))
                
                row = cursor.fetchone()
                if row and row[0] > 0:
                    stats['success_rate_24h'] = (row[1] / row[0]) * 100
                    stats['total_runs_24h'] = row[0]
                    stats['failed_runs_24h'] = row[0] - row[1]
                else:
                    stats['success_rate_24h'] = 0.0
                    stats['total_runs_24h'] = 0
                    stats['failed_runs_24h'] = 0
                    
                # Success rate in last 7 days
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END) as success
                    FROM cron_entries 
                    WHERE timestamp >= ?
                """, (week_ago,))
                
                row = cursor.fetchone()
                if row and row[0] > 0:
                    stats['success_rate_7d'] = (row[1] / row[0]) * 100
                    stats['total_runs_7d'] = row[0]
                else:
                    stats['success_rate_7d'] = 0.0
                    stats['total_runs_7d'] = 0
                    
                # Most recent failure
                cursor = conn.execute("""
                    SELECT timestamp, message 
                    FROM cron_entries 
                    WHERE exit_code != 0 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if row:
                    stats['last_failure_time'] = row[0]
                    stats['last_failure_message'] = row[1]
                else:
                    stats['last_failure_time'] = None
                    stats['last_failure_message'] = None
                    
                # Average time between runs (estimate)
                cursor = conn.execute("""
                    SELECT timestamp 
                    FROM cron_entries 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """)
                
                timestamps = [row[0] for row in cursor.fetchall()]
                if len(timestamps) > 1:
                    # Calculate intervals between consecutive runs
                    intervals = []
                    for i in range(len(timestamps) - 1):
                        try:
                            t1 = datetime.fromisoformat(timestamps[i].replace('Z', '+00:00'))
                            t2 = datetime.fromisoformat(timestamps[i+1].replace('Z', '+00:00'))
                            interval = abs((t1 - t2).total_seconds())
                            intervals.append(interval)
                        except:
                            continue
                            
                    if intervals:
                        stats['avg_run_interval_seconds'] = sum(intervals) / len(intervals)
                        stats['avg_run_interval_minutes'] = stats['avg_run_interval_seconds'] / 60
                    else:
                        stats['avg_run_interval_seconds'] = 0
                        stats['avg_run_interval_minutes'] = 0
                else:
                    stats['avg_run_interval_seconds'] = 0
                    stats['avg_run_interval_minutes'] = 0
                    
                # Cache stats
                computed_at = now.isoformat()
                for metric, value in stats.items():
                    if isinstance(value, (int, float)):
                        conn.execute("""
                            INSERT OR REPLACE INTO stats_cache (metric, value, computed_at)
                            VALUES (?, ?, ?)
                        """, (metric, value, computed_at))
                        
                conn.commit()
                logger.debug("Statistics computed and cached")
                return stats
                
        except Exception as e:
            logger.error(f"Failed to compute statistics: {e}")
            return {}
            
    def display_stats(self):
        """Display current statistics."""
        stats = self.compute_stats()
        
        print("\n" + "="*60)
        print("📊 CRON COLLECTOR STATISTICS")
        print("="*60)
        
        print(f"\n📈 Last 24 Hours:")
        print(f"   Total runs: {stats.get('total_runs_24h', 0)}")
        print(f"   Success rate: {stats.get('success_rate_24h', 0):.1f}%")
        print(f"   Failed runs: {stats.get('failed_runs_24h', 0)}")
        
        print(f"\n📊 Last 7 Days:")
        print(f"   Total runs: {stats.get('total_runs_7d', 0)}")
        print(f"   Success rate: {stats.get('success_rate_7d', 0):.1f}%")
        
        if stats.get('avg_run_interval_minutes', 0) > 0:
            print(f"\n⏱️  Average interval: {stats.get('avg_run_interval_minutes', 0):.1f} minutes")
            
        if stats.get('last_failure_time'):
            print(f"\n🚨 Last failure:")
            print(f"   Time: {stats.get('last_failure_time')}")
            print(f"   Message: {stats.get('last_failure_message', '')[:80]}...")
        else:
            print(f"\n✅ No recent failures recorded")
            
        # Database info
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM cron_entries")
                total_entries = cursor.fetchone()[0]
                print(f"\n💾 Database: {total_entries} total entries")
        except:
            print(f"\n💾 Database: Unable to read")
            
        print("="*60)
        
    def watch_mode(self):
        """Run in watch mode, continuously monitoring for new entries."""
        logger.info("Starting watch mode...")
        self.running = True
        last_stats_time = 0
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal")
            self.running = False
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            while self.running:
                # Process new entries
                self.process_new_entries()
                
                # Compute stats periodically
                current_time = time.time()
                if current_time - last_stats_time > STATS_INTERVAL:
                    self.compute_stats()
                    last_stats_time = current_time
                    
                time.sleep(CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("Watch mode interrupted by user")
        except Exception as e:
            logger.error(f"Watch mode error: {e}")
        finally:
            self.running = False
            logger.info("Watch mode stopped")
            
    def run_daemon(self):
        """Run as a background daemon with PID file management."""
        log_file_path = Path.home() / ".cron_dash" / "daemon.log"
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure the PID file directory exists
        self.pid_file_path.parent.mkdir(parents=True, exist_ok=True)
        pid_lock_file = pidfile.PIDLockFile(self.pid_file_path)

        # Define the daemon context
        context = daemon.DaemonContext(
            working_directory=os.getcwd(),
            umask=0o022,
            pidfile=pid_lock_file,
            stdout=open(log_file_path, 'a+'),
            stderr=open(log_file_path, 'a+')
        )

        # Set up signal handling for graceful shutdown within the daemon context
        def sigterm_handler(signum, frame):
            logger.info("Daemon received SIGTERM signal. Shutting down.")
            self.running = False

        context.signal_map = {
            signal.SIGTERM: sigterm_handler,
            signal.SIGHUP: None,  # Example: could be used to reload config
        }

        logger.info("Starting daemon mode...")
        try:
            with context:
                logger.info("Daemon started successfully.")
                self.watch_mode()
            logger.info("Daemon stopped.")
        except Exception as e:
            logger.error(f"Error in daemon context: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cron Collector Data Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Watch for new entries (default)
  %(prog)s --parse-existing     # Parse all existing entries
  %(prog)s --stats              # Show current statistics  
  %(prog)s --daemon             # Run as background daemon
        """
    )
    
    parser.add_argument(
        "--parse-existing",
        action="store_true",
        help="Parse all existing entries from JSONL file"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true", 
        help="Display current statistics and exit"
    )
    
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as background daemon"
    )
    
    parser.add_argument(
        "--check-interval",
        type=int,
        default=CHECK_INTERVAL,
        help=f"Check interval in seconds (default: {CHECK_INTERVAL})"
    )
    
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DB_PATH,
        help=f"Database path (default: {DB_PATH})"
    )
    
    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Update check interval
    check_interval = args.check_interval
    
    try:
        collector = CronCollector(db_path=args.db_path, log_level=args.log_level)
        
        if args.parse_existing:
            count = collector.parse_existing_entries()
            print(f"✅ Parsed {count} existing entries")
            
        elif args.stats:
            collector.display_stats()
            
        elif args.daemon:
            collector.run_daemon()
            
        else:
            # Default watch mode
            print("🚀 Starting Cron Collector (Ctrl+C to stop)")
            print(f"📁 Watching: {collector.jsonl_path}")
            print(f"💾 Database: {collector.db_path}")
            print(f"⏱️  Check interval: {CHECK_INTERVAL} seconds")
            collector.watch_mode()
            
    except KeyboardInterrupt:
        print("\n👋 Cron Collector stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
