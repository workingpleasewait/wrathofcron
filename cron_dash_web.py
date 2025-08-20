#!/usr/bin/env python3
"""
Cron Dashboard Web Interface

A Flask web application that displays cron job monitoring data with:
- Plotly line chart of runtimes over 7 days
- Heat-map of success/fail by hour  
- Colorful status banner ("All Good" / "Issues")
- Auto-refresh every 30 seconds

REQUIREMENTS:
- Flask
- Plotly
- SQLite database created by cron_collector.py

USAGE:
    flask run
    # or
    python cron_dash_web.py
    
    View at http://localhost:5001

The dashboard reads from ~/.cron_dash/ladder.db and displays interactive charts.
"""

from flask import Flask, render_template, g, request
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import plotly.graph_objs as go
import plotly.utils
import statistics
import subprocess
import re
import socket

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Configuration from environment variables with validation
DEBUG = os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes', 'on')
HOST = os.getenv('HOST', '0.0.0.0')

# Validate PORT
try:
    PORT = int(os.getenv('PORT', '5001'))
    if not (1 <= PORT <= 65535):
        raise ValueError(f"PORT must be between 1 and 65535, got {PORT}")
except ValueError as e:
    print(f"Warning: Invalid PORT environment variable: {e}. Using default 5001.")
    PORT = 5001

# Basic Auth configuration with validation
AUTH_USERNAME = os.getenv('AUTH_USERNAME', 'admin')
AUTH_PASSWORD = os.getenv('AUTH_PASSWORD', 'password')

# Validate auth credentials
if len(AUTH_USERNAME.strip()) == 0:
    print("Warning: AUTH_USERNAME is empty. Using default 'admin'.")
    AUTH_USERNAME = 'admin'

if len(AUTH_PASSWORD) < 8:
    print("Warning: AUTH_PASSWORD should be at least 8 characters for security.")

# Store password hash for security
AUTH_PASSWORD_HASH = generate_password_hash(AUTH_PASSWORD)

# Database path (matches cron_collector.py)
DB_PATH = Path.home() / ".cron_dash" / "ladder.db"

class CronWebDashboard:
    """Web dashboard for cron job monitoring."""
    
    def __init__(self):
        self.db_path = DB_PATH
        
    
    def get_last_run_status(self) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """Get the most recent run status."""
        conn = get_db()
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
    
    def get_7day_runs(self) -> List[Tuple[str, int, str]]:
        """Get all runs in the last 7 days."""
        conn = get_db()
        if not conn:
            return []
            
        try:
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor = conn.execute("""
                SELECT timestamp, exit_code, message
                FROM cron_entries 
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """, (week_ago,))
            return cursor.fetchall()
        except Exception:
            return []
    
    def get_24h_runs(self) -> List[Tuple[str, int, str]]:
        """Get all runs in the last 24 hours."""
        conn = get_db()
        if not conn:
            return []
            
        try:
            day_ago = (datetime.now() - timedelta(days=1)).isoformat()
            cursor = conn.execute("""
                SELECT timestamp, exit_code, message
                FROM cron_entries 
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """, (day_ago,))
            return cursor.fetchall()
        except Exception:
            return []
    
    def calculate_run_intervals(self, runs: List[Tuple[str, int, str]]) -> List[Tuple[datetime, float]]:
        """Calculate intervals between runs as proxy for runtime."""
        intervals = []
        for i in range(1, len(runs)):
            try:
                t1 = datetime.fromisoformat(runs[i-1][0].replace('Z', '+00:00'))
                t2 = datetime.fromisoformat(runs[i][0].replace('Z', '+00:00'))
                interval = (t2 - t1).total_seconds()
                intervals.append((t2.replace(tzinfo=None), interval))
            except:
                continue
        return intervals
    
    def create_runtime_chart(self) -> str:
        """Create Plotly line chart of runtimes over 7 days."""
        runs = self.get_7day_runs()
        
        if not runs:
            # Empty chart
            fig = go.Figure()
            fig.add_annotation(
                text="No data available",
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                showarrow=False,
                font={"size": 16, "color": "gray"}
            )
            fig.update_layout(
                title="Runtime Intervals Over 7 Days",
                xaxis_title="Time",
                yaxis_title="Interval (seconds)",
                height=400,
                showlegend=False
            )
        else:
            intervals = self.calculate_run_intervals(runs)
            
            if not intervals:
                fig = go.Figure()
                fig.add_annotation(
                    text="Insufficient data for intervals",
                    x=0.5, y=0.5,
                    xref="paper", yref="paper",
                    showarrow=False,
                    font={"size": 16, "color": "gray"}
                )
            else:
                timestamps, interval_values = zip(*intervals)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=timestamps,
                    y=interval_values,
                    mode='lines+markers',
                    name='Runtime Intervals',
                    line=dict(color='blue', width=2),
                    marker=dict(size=6)
                ))
                
                fig.update_layout(
                    title="Runtime Intervals Over 7 Days",
                    xaxis_title="Time",
                    yaxis_title="Interval (seconds)",
                    height=400,
                    hovermode='x unified'
                )
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    def create_heatmap(self) -> str:
        """Create Plotly heatmap of success/fail by hour."""
        runs = self.get_7day_runs()
        
        if not runs:
            # Empty heatmap
            fig = go.Figure()
            fig.add_annotation(
                text="No data available",
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                showarrow=False,
                font={"size": 16, "color": "gray"}
            )
            fig.update_layout(
                title="Success/Failure Heatmap by Hour",
                height=300
            )
        else:
            # Create 7x24 matrix (7 days, 24 hours)
            # 0 = Sunday, 1 = Monday, etc.
            heatmap_data = [[0 for _ in range(24)] for _ in range(7)]
            success_data = [[0 for _ in range(24)] for _ in range(7)]
            total_data = [[0 for _ in range(24)] for _ in range(7)]
            
            for timestamp, exit_code, _ in runs:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    day_of_week = dt.weekday()  # 0=Monday
                    # Convert to Sunday=0 format
                    day_of_week = (day_of_week + 1) % 7
                    hour = dt.hour
                    
                    total_data[day_of_week][hour] += 1
                    if exit_code == 0:
                        success_data[day_of_week][hour] += 1
                except:
                    continue
            
            # Calculate success rates (0-100%)
            for day in range(7):
                for hour in range(24):
                    if total_data[day][hour] > 0:
                        success_rate = (success_data[day][hour] / total_data[day][hour]) * 100
                        heatmap_data[day][hour] = success_rate
                    else:
                        heatmap_data[day][hour] = None  # No data
            
            days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
            hours = [f"{h:02d}" for h in range(24)]
            
            fig = go.Figure(data=go.Heatmap(
                z=heatmap_data,
                x=hours,
                y=days,
                colorscale=[[0, 'red'], [0.5, 'yellow'], [1, 'green']],
                hoverongaps=False,
                hovertemplate='<b>%{y} %{x}:00</b><br>' +
                             'Success Rate: %{z:.1f}%<br>' +
                             '<extra></extra>',
                zmin=0,
                zmax=100
            ))
            
            fig.update_layout(
                title="Success Rate Heatmap by Day and Hour",
                xaxis_title="Hour of Day",
                yaxis_title="Day of Week",
                height=300
            )
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    def get_status_info(self) -> Dict:
        """Get overall status information for the banner."""
        timestamp, exit_code, message = self.get_last_run_status()
        runs_24h = self.get_24h_runs()
        
        if not runs_24h:
            return {
                'status': 'NO_DATA',
                'message': 'No recent data',
                'last_run': None,
                'success_rate': 0,
                'total_runs': 0,
                'color': 'warning'
            }
        
        success_count = sum(1 for _, exit_code, _ in runs_24h if exit_code == 0)
        success_rate = (success_count / len(runs_24h)) * 100 if runs_24h else 0
        
        # Determine overall status
        if success_rate >= 90:
            status = 'ALL_GOOD'
            color = 'success'
            status_message = 'All Good'
        elif success_rate >= 70:
            status = 'MINOR_ISSUES'
            color = 'warning'
            status_message = 'Minor Issues'
        else:
            status = 'ISSUES'
            color = 'danger'
            status_message = 'Issues Detected'
        
        # Format last run time
        last_run_formatted = None
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_ago = datetime.now() - dt.replace(tzinfo=None)
                
                if time_ago.total_seconds() < 60:
                    last_run_formatted = f"{int(time_ago.total_seconds())}s ago"
                elif time_ago.total_seconds() < 3600:
                    last_run_formatted = f"{int(time_ago.total_seconds() / 60)}m ago"
                else:
                    last_run_formatted = f"{int(time_ago.total_seconds() / 3600)}h ago"
            except:
                last_run_formatted = "Unknown"
        
        return {
            'status': status,
            'message': status_message,
            'last_run': last_run_formatted,
            'success_rate': success_rate,
            'total_runs': len(runs_24h),
            'color': color,
            'last_exit_code': exit_code
        }
    
    def parse_cron_schedule(self, schedule: str) -> str:
        """Convert cron schedule to human readable format."""
        # Remove leading/trailing whitespace and normalize
        schedule = schedule.strip()
        
        # Handle special schedules
        special_schedules = {
            '@yearly': 'Once a year (January 1st at midnight)',
            '@annually': 'Once a year (January 1st at midnight)', 
            '@monthly': 'Once a month (1st day at midnight)',
            '@weekly': 'Once a week (Sunday at midnight)',
            '@daily': 'Once a day (at midnight)',
            '@midnight': 'Once a day (at midnight)',
            '@hourly': 'Once an hour (at minute 0)',
            '@reboot': 'At system startup'
        }
        
        if schedule in special_schedules:
            return special_schedules[schedule]
        
        # Parse standard cron format: minute hour day month weekday
        parts = schedule.split()
        if len(parts) != 5:
            return schedule  # Return as-is if not standard format
        
        minute, hour, day, month, weekday = parts
        
        # Build human readable description
        description_parts = []
        
        # Handle minute
        if minute == '*':
            pass  # Every minute
        elif minute.startswith('*/'):
            interval = minute[2:]
            description_parts.append(f"every {interval} minutes")
        elif '-' in minute:
            start, end = minute.split('-')
            description_parts.append(f"minutes {start}-{end}")
        elif ',' in minute:
            minutes = minute.replace(',', ', ')
            description_parts.append(f"at minutes {minutes}")
        else:
            description_parts.append(f"at minute {minute}")
        
        # Handle hour
        if hour == '*':
            if not description_parts or 'every' not in description_parts[0]:
                description_parts.append("every hour")
        elif hour.startswith('*/'):
            interval = hour[2:]
            description_parts.append(f"every {interval} hours")
        elif '-' in hour:
            start, end = hour.split('-')
            description_parts.append(f"between {start}:00-{end}:00")
        elif ',' in hour:
            hours = hour.replace(',', ', ')
            description_parts.append(f"at hours {hours}")
        else:
            hour_12 = int(hour)
            am_pm = 'AM' if hour_12 < 12 else 'PM'
            if hour_12 == 0:
                hour_12 = 12
            elif hour_12 > 12:
                hour_12 -= 12
            description_parts.append(f"at {hour_12}:00 {am_pm}")
        
        # Handle day of month
        if day != '*':
            if day.startswith('*/'):
                interval = day[2:]
                description_parts.append(f"every {interval} days")
            elif ',' in day:
                days = day.replace(',', ', ')
                description_parts.append(f"on days {days}")
            else:
                description_parts.append(f"on day {day}")
        
        # Handle month
        if month != '*':
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            if month.isdigit():
                month_num = int(month) - 1
                if 0 <= month_num < 12:
                    description_parts.append(f"in {month_names[month_num]}")
        
        # Handle weekday
        if weekday != '*':
            weekday_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
            if weekday.isdigit():
                day_num = int(weekday)
                if 0 <= day_num < 7:
                    description_parts.append(f"on {weekday_names[day_num]}")
            elif '1-5' in weekday:
                description_parts.append("on weekdays")
            elif '0,6' in weekday or '6,0' in weekday:
                description_parts.append("on weekends")
        
        if not description_parts:
            return "Every minute"
        
        return " ".join(description_parts).capitalize()
    
    def get_cron_jobs(self) -> List[Dict]:
        """Get list of installed cron jobs with human readable info."""
        try:
            # Get current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode != 0:
                return []
            
            # Get current machine info
            hostname = socket.gethostname()
            machine_name = hostname.split('.')[0]  # Get short hostname
            
            # Try to get a more friendly machine name
            try:
                system_info = subprocess.run(['system_profiler', 'SPHardwareDataType'], 
                                           capture_output=True, text=True)
                if system_info.returncode == 0:
                    for line in system_info.stdout.split('\n'):
                        if 'Model Name:' in line:
                            model_line = line.strip()
                            if 'MacBook Air' in model_line:
                                machine_type = '💻 MacBook Air'
                            elif 'MacBook Pro' in model_line:
                                machine_type = '💻 MacBook Pro'
                            elif 'iMac' in model_line:
                                machine_type = '🖥️ iMac'
                            elif 'Mac mini' in model_line:
                                machine_type = '🖥️ Mac mini'
                            elif 'Mac Studio' in model_line:
                                machine_type = '🖥️ Mac Studio'
                            elif 'Mac Pro' in model_line:
                                machine_type = '🖥️ Mac Pro'
                            else:
                                machine_type = '💻 Mac'
                            break
                    else:
                        machine_type = '💻 Mac'
                else:
                    machine_type = '💻 Mac'
            except:
                machine_type = '💻 Mac'
            
            cron_lines = result.stdout.strip().split('\n')
            jobs = []
            
            current_section = "General"
            
            for line in cron_lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Check for section headers in comments
                if line.startswith('#'):
                    if 'SHARED CRON JOBS' in line:
                        current_section = "Shared Jobs"
                    elif 'MACHINE-SPECIFIC' in line:
                        current_section = "Machine-Specific"
                    continue
                
                # Skip comment lines that aren't jobs
                if line.startswith('#'):
                    continue
                
                # Parse cron job line
                # Format: schedule + command
                parts = line.split(None, 5)  # Split into max 6 parts
                if len(parts) < 6:
                    continue
                
                schedule = ' '.join(parts[:5])
                command = parts[5]
                
                # Extract meaningful info from command
                job_name = "Unknown Task"
                job_type = "System"
                job_description = command
                
                # Determine job type and name based on command
                if 'ladder' in command.lower():
                    job_name = "Coinbase Ladder Monitor"
                    job_type = "Trading"
                    job_description = "Monitors coinbase trading ladder status and logs results"
                elif 'cron_collector' in command:
                    job_name = "Cron Data Collector"
                    job_type = "Monitoring"
                    job_description = "Collects and analyzes cron job execution data"
                elif 'pmset' in command:
                    job_name = "Battery Optimization"
                    job_type = "System"
                    job_description = "Optimizes MacBook battery settings"
                elif 'find /tmp' in command:
                    job_name = "Temp File Cleanup"
                    job_type = "Maintenance"
                    job_description = "Cleans up old temporary files"
                elif 'brew' in command:
                    job_name = "Homebrew Update"
                    job_type = "Maintenance"
                    job_description = "Updates Homebrew packages and formulas"
                elif 'daily-task' in command:
                    job_name = "Daily Task"
                    job_type = "Scheduled"
                    job_description = "Executes daily maintenance tasks"
                elif 'hourly-task' in command:
                    job_name = "Hourly Task"
                    job_type = "Scheduled"
                    job_description = "Executes hourly maintenance tasks"
                
                # Determine if job is active (not commented out)
                is_active = True
                status = "Active"
                status_color = "success"
                
                # Get next run time (simplified)
                schedule_human = self.parse_cron_schedule(schedule)
                
                jobs.append({
                    'name': job_name,
                    'type': job_type,
                    'schedule': schedule,
                    'schedule_human': schedule_human,
                    'command': command,
                    'description': job_description,
                    'section': current_section,
                    'status': status,
                    'status_color': status_color,
                    'is_active': is_active,
                    'hostname': machine_name,
                    'machine_type': machine_type,
                    'machine_display': f"{machine_type} ({machine_name})"
                })
            
            return jobs
            
        except Exception as e:
            print(f"Error getting cron jobs: {e}")
            return []

# Database connection management
def get_db():
    """Get database connection stored in g."""
    if 'db' not in g:
        if DB_PATH.exists():
            g.db = sqlite3.connect(DB_PATH)
        else:
            g.db = None
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Basic Authentication
def requires_auth(f):
    """Decorator that requires HTTP Basic Authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def check_auth(username, password):
    """Check if username/password combination is valid."""
    return username == AUTH_USERNAME and check_password_hash(AUTH_PASSWORD_HASH, password)

def authenticate():
    """Send 401 response that enables basic auth."""
    return ('Authentication required', 401, 
            {'WWW-Authenticate': 'Basic realm="Cron Dashboard"'})

dashboard = CronWebDashboard()

@app.route('/')
@limiter.limit("30 per minute")
@requires_auth
def index():
    """Main dashboard page."""
    runtime_chart = dashboard.create_runtime_chart()
    heatmap_chart = dashboard.create_heatmap()
    status_info = dashboard.get_status_info()
    cron_jobs = dashboard.get_cron_jobs()
    
    return render_template(
        'dashboard.html',
        runtime_chart=runtime_chart,
        heatmap_chart=heatmap_chart,
        status_info=status_info,
        cron_jobs=cron_jobs,
        datetime=datetime
    )

if __name__ == '__main__':
    app.run(debug=DEBUG, host=HOST, port=PORT)
