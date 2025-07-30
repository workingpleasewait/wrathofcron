#!/usr/bin/env python3
"""
Cron Dashboard TUI

A rich-based terminal dashboard that displays:
- Live ticker of last run time & status (✓/✗ with colour)
- 24h bar of run outcomes (green/red blocks)
- Table of last 10 runs with timestamp, duration, result
- Rolling graphs (rich Live + sparklines) for runtime & success rate

The script auto-refreshes every second; launch it with `python cron_dash_tui.py`.

REQUIREMENTS:
- Python 3.7+
- rich library (pip install rich)
- SQLite database created by cron_collector.py

USAGE:
    python cron_dash_tui.py
    
The dashboard reads from ~/.cron_dash/ladder.db and displays:

┌─ Live Status ─────────────────┐  ┌─ 24-Hour Activity ────────────┐
│ Last Run: ✓ SUCCESS 09:15:30  │  │ ████████░░░░░░░░░░░░░░░░░░░░░░░░ │
│           (2m ago)            │  │ Success Rate: 85.5% (47/55)    │
└───────────────────────────────┘  └─────────────────────────────────┘

┌─ Recent Runs ─────────────────────────────────────┐ ┌─ Rolling Metrics ─┐
│ Time     Status  Message                          │ │ Success: ▅▆▇█▇▆▅  │
│ 09:15:30 ✓ OK    Ladder order executed           │ │ Runtime: ▃▄▅▄▃▂▁  │
│ 09:10:30 ✓ OK    Balance check completed         │ └───────────────────┘
│ 09:05:30 ✗ 1     Network timeout error           │
└───────────────────────────────────────────────────┘

KEYBOARDS:
- Ctrl+C: Exit dashboard

COLOR CODING:
- Green: Success (exit code 0)
- Red: Failure (exit code != 0)
- Blue: Status information
- Yellow: Metrics and graphs
"""

import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statistics

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.columns import Columns
from rich.bar import Bar
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.rule import Rule
from rich import box

# Database path (matches cron_collector.py)
DB_PATH = Path.home() / ".cron_dash" / "ladder.db"
REFRESH_INTERVAL = 1.0  # seconds


class CronDashboard:
    """Rich-based terminal dashboard for cron job monitoring."""
    
    def __init__(self):
        self.console = Console()
        self.db_path = DB_PATH
        self.success_history = []  # For sparkline
        self.runtime_history = []  # For sparkline (using intervals as proxy)
        
    def get_db_connection(self) -> Optional[sqlite3.Connection]:
        """Get database connection if available."""
        try:
            if not self.db_path.exists():
                return None
            return sqlite3.connect(self.db_path)
        except Exception:
            return None
    
    def get_last_run_status(self) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """Get the most recent run status."""
        conn = self.get_db_connection()
        if not conn:
            return None, None, None
            
        try:
            cursor = conn.execute("""
                SELECT timestamp, exit_code, message 
                FROM cron_entries 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return row[0], row[1], row[2]
            return None, None, None
        except Exception:
            return None, None, None
        finally:
            conn.close()
    
    def get_24h_runs(self) -> List[Tuple[str, int]]:
        """Get all runs in the last 24 hours."""
        conn = self.get_db_connection()
        if not conn:
            return []
            
        try:
            day_ago = (datetime.now() - timedelta(days=1)).isoformat()
            cursor = conn.execute("""
                SELECT timestamp, exit_code 
                FROM cron_entries 
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """, (day_ago,))
            return cursor.fetchall()
        except Exception:
            return []
        finally:
            conn.close()
    
    def get_recent_runs(self, limit: int = 10) -> List[Tuple[str, int, str]]:
        """Get the most recent runs."""
        conn = self.get_db_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.execute("""
                SELECT timestamp, exit_code, message 
                FROM cron_entries 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()
        except Exception:
            return []
        finally:
            conn.close()
    
    def calculate_run_duration(self, runs: List[Tuple[str, int]]) -> List[float]:
        """Calculate approximate durations between runs."""
        durations = []
        for i in range(1, len(runs)):
            try:
                t1 = datetime.fromisoformat(runs[i-1][0].replace('Z', '+00:00'))
                t2 = datetime.fromisoformat(runs[i][0].replace('Z', '+00:00'))
                duration = abs((t1 - t2).total_seconds())
                durations.append(duration)
            except:
                durations.append(0.0)
        return durations
    
    def create_sparkline(self, data: List[float], width: int = 20) -> str:
        """Create a simple ASCII sparkline."""
        if not data or len(data) == 0:
            return "─" * width
            
        if len(data) == 1:
            return "█" + "─" * (width - 1)
            
        # Normalize data to 0-7 range for different bar heights
        min_val = min(data)
        max_val = max(data)
        
        if max_val == min_val:
            return "─" * width
            
        # Unicode block characters for different heights
        bars = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        
        # Sample data to fit width
        if len(data) > width:
            step = len(data) / width
            sampled = [data[int(i * step)] for i in range(width)]
        else:
            sampled = data + [data[-1]] * (width - len(data))
            
        result = ""
        for value in sampled:
            normalized = (value - min_val) / (max_val - min_val)
            bar_index = int(normalized * (len(bars) - 1))
            result += bars[bar_index]
            
        return result
    
    def create_status_ticker(self) -> Panel:
        """Create the live status ticker panel."""
        timestamp, exit_code, message = self.get_last_run_status()
        
        if timestamp is None:
            status_text = Text("No runs recorded", style="dim")
            time_text = Text("─", style="dim")
        else:
            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_ago = datetime.now() - dt.replace(tzinfo=None)
                
                if time_ago.total_seconds() < 60:
                    time_text = Text(f"{int(time_ago.total_seconds())}s ago", style="dim")
                elif time_ago.total_seconds() < 3600:
                    time_text = Text(f"{int(time_ago.total_seconds() / 60)}m ago", style="dim")
                else:
                    time_text = Text(f"{int(time_ago.total_seconds() / 3600)}h ago", style="dim")
                    
                # Format time
                time_display = dt.strftime("%H:%M:%S")
                time_text = Text(f"{time_display} ({time_text.plain})", style="dim")
                
            except:
                time_text = Text(timestamp[:19], style="dim")
            
            # Status with color
            if exit_code == 0:
                status_text = Text("✓ SUCCESS", style="bold green")
            else:
                status_text = Text(f"✗ FAILED ({exit_code})", style="bold red")
        
        content = Columns([
            Text("Last Run:", style="bold"),
            status_text,
            time_text
        ], align="left")
        
        return Panel(
            Align.center(content),
            title="[bold blue]Live Status",
            border_style="blue",
            padding=(0, 1)
        )
    
    def create_24h_bar(self) -> Panel:
        """Create 24-hour outcome bar chart."""
        runs = self.get_24h_runs()
        
        if not runs:
            bar_content = Text("No data available", style="dim")
        else:
            # Create blocks representing success/failure
            success_count = sum(1 for _, exit_code in runs if exit_code == 0)
            failure_count = len(runs) - success_count
            
            # Calculate success rate
            success_rate = (success_count / len(runs)) * 100 if runs else 0
            
            # Create visual bar (50 characters max)
            bar_width = min(50, len(runs))
            if bar_width < len(runs):
                # Sample runs to fit display width
                step = len(runs) / bar_width
                sampled_runs = [runs[int(i * step)] for i in range(bar_width)]
            else:
                sampled_runs = runs
            
            bar_text = Text()
            for _, exit_code in sampled_runs:
                if exit_code == 0:
                    bar_text.append("█", style="green")
                else:
                    bar_text.append("█", style="red")
            
            # Add padding if needed
            if len(sampled_runs) < 50:
                bar_text.append("░" * (50 - len(sampled_runs)), style="dim")
            
            stats_text = Text(f"Success Rate: {success_rate:.1f}% ({success_count}/{len(runs)} runs)", style="dim")
            bar_content = Text.assemble(bar_text, "\n", stats_text)
        
        return Panel(
            bar_content,
            title="[bold green]24-Hour Activity",
            border_style="green",
            padding=(0, 1)
        )
    
    def create_recent_runs_table(self) -> Panel:
        """Create table of recent runs."""
        runs = self.get_recent_runs(10)
        
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
        table.add_column("Time", style="dim", width=12)
        table.add_column("Status", width=8)
        table.add_column("Message", style="dim", no_wrap=False)
        
        if not runs:
            table.add_row("─", "─", "No runs recorded")
        else:
            for timestamp, exit_code, message in runs:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = timestamp[:8]
                
                if exit_code == 0:
                    status = Text("✓ OK", style="green")
                else:
                    status = Text(f"✗ {exit_code}", style="red")
                
                # Truncate message if too long
                display_message = message[:60] + "..." if len(message) > 60 else message
                
                table.add_row(time_str, status, display_message)
        
        return Panel(
            table,
            title="[bold magenta]Recent Runs",
            border_style="magenta",
            padding=(0, 1)
        )
    
    def create_rolling_graphs(self) -> Panel:
        """Create rolling graphs for success rate and runtime."""
        runs = self.get_24h_runs()
        
        if not runs:
            graph_content = Text("No data for graphs", style="dim")
        else:
            # Update success history
            recent_success_rate = (sum(1 for _, exit_code in runs[-20:] if exit_code == 0) / min(len(runs), 20)) * 100
            self.success_history.append(recent_success_rate)
            if len(self.success_history) > 30:
                self.success_history.pop(0)
            
            # Update runtime history (using intervals as proxy)
            durations = self.calculate_run_duration(runs[-10:])
            if durations:
                avg_duration = statistics.mean(durations)
                self.runtime_history.append(avg_duration)
                if len(self.runtime_history) > 30:
                    self.runtime_history.pop(0)
            
            # Create sparklines
            success_sparkline = self.create_sparkline(self.success_history, 40)
            runtime_sparkline = self.create_sparkline(self.runtime_history, 40)
            
            current_success = f"{recent_success_rate:.1f}%"
            current_runtime = f"{avg_duration:.1f}s" if durations else "─"
            
            graph_content = Text.assemble(
                Text("Success Rate: ", style="dim"),
                Text(success_sparkline, style="green"),
                Text(f" {current_success}", style="bold green"),
                Text("\n"),
                Text("Avg Interval: ", style="dim"),
                Text(runtime_sparkline, style="blue"),
                Text(f" {current_runtime}", style="bold blue")
            )
        
        return Panel(
            graph_content,
            title="[bold yellow]Rolling Metrics",
            border_style="yellow",
            padding=(0, 1)
        )
    
    def create_dashboard_layout(self) -> Layout:
        """Create the main dashboard layout."""
        layout = Layout()
        
        # Split into top and bottom
        layout.split_column(
            Layout(name="top", ratio=1),
            Layout(name="bottom", ratio=2)
        )
        
        # Split top into status and 24h bar
        layout["top"].split_row(
            Layout(name="status", ratio=1),
            Layout(name="bar", ratio=1)
        )
        
        # Split bottom into table and graphs
        layout["bottom"].split_row(
            Layout(name="table", ratio=2),
            Layout(name="graphs", ratio=1)
        )
        
        return layout
    
    def update_dashboard(self, layout: Layout):
        """Update all dashboard components."""
        layout["status"].update(self.create_status_ticker())
        layout["bar"].update(self.create_24h_bar())
        layout["table"].update(self.create_recent_runs_table())
        layout["graphs"].update(self.create_rolling_graphs())
    
    def run(self):
        """Run the dashboard with live updates."""
        # Check if database exists
        if not self.db_path.exists():
            self.console.print(f"[red]Database not found at {self.db_path}[/red]")
            self.console.print("[yellow]Run 'python cron_collector.py --parse-existing' first[/yellow]")
            return
        
        layout = self.create_dashboard_layout()
        
        # Create header
        header = Panel(
            Align.center(
                Text("🚀 CRON DASHBOARD 🚀", style="bold bright_blue"),
            ),
            style="bright_blue",
            padding=(0, 1)
        )
        
        # Create footer
        footer = Panel(
            Align.center(
                Text("Press Ctrl+C to exit • Refreshes every second", style="dim"),
            ),
            style="dim",
            padding=(0, 1)
        )
        
        try:
            with Live(
                layout,
                console=self.console,
                screen=True,
                redirect_stderr=False,
                redirect_stdout=False,
                refresh_per_second=1
            ) as live:
                # Show header
                self.console.print(header)
                
                while True:
                    self.update_dashboard(layout)
                    live.update(layout)
                    time.sleep(REFRESH_INTERVAL)
                    
        except KeyboardInterrupt:
            self.console.print(footer)
            self.console.print("[green]Dashboard stopped by user[/green]")


def main():
    """Main entry point."""
    dashboard = CronDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
