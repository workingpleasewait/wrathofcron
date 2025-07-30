# Cron Dashboard Web Interface

A Flask web application that provides real-time monitoring of cron job execution with interactive visualizations.

## Features

- **Plotly Line Chart**: Shows runtime intervals over the last 7 days
- **Heatmap Visualization**: Displays success/failure rates by hour and day of the week
- **Status Banner**: Color-coded status indicator ("All Good", "Minor Issues", "Issues Detected")
- **Auto-refresh**: Page automatically refreshes every 30 seconds
- **Responsive Design**: Works on desktop and mobile devices

## Requirements

- Python 3.7+
- Flask
- Plotly
- SQLite database created by `cron_collector.py`

## Installation

```bash
pip install flask plotly
```

## Usage

### Option 1: Direct Python execution
```bash
python cron_dash_web.py
```

### Option 2: Using Flask CLI
```bash
export FLASK_APP=cron_dash_web.py
flask run --port 5001
```

### Option 3: Using Flask run command
```bash
flask run --app cron_dash_web --port 5001
```

## Viewing the Dashboard

Once the application is running, open your web browser and navigate to:

**http://localhost:5001**

## Dashboard Components

### Status Banner
- **Green (✅)**: Success rate ≥ 90% - "All Good"
- **Yellow (⚠️)**: Success rate 70-89% - "Minor Issues"  
- **Red (❌)**: Success rate < 70% - "Issues Detected"

Shows:
- Current system status
- Last run time and result
- 24-hour success rate percentage
- Total number of runs in the last 24 hours

### Runtime Intervals Chart
- Line chart showing intervals between cron job executions
- Covers the last 7 days of data
- Interactive tooltips with timestamp and interval details
- Blue line with markers for easy visualization

### Success Rate Heatmap
- Visual representation of success rates by hour and day
- Color-coded: Red (0%) → Yellow (50%) → Green (100%)
- Shows patterns of when jobs succeed or fail
- Hover tooltips show exact success percentages

## Data Source

The dashboard reads from the SQLite database located at:
```
~/.cron_dash/ladder.db
```

This database is created and populated by the `cron_collector.py` script. Make sure the collector is running to see live data.

## Auto-Refresh

The page automatically refreshes every 30 seconds using HTML meta-refresh. This ensures you always see the latest data without manual page reloads.

## Network Access

The Flask app runs on all interfaces (0.0.0.0) by default, so it can be accessed from other devices on your network at:
```
http://YOUR_IP_ADDRESS:5001
```

## Troubleshooting

### Port 5001 Already in Use
If port 5001 is occupied, modify the port in `cron_dash_web.py` at the bottom of the file:
```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)  # Change port here
```

### No Data Showing
1. Verify the database exists: `ls ~/.cron_dash/ladder.db`
2. Check if the collector is running: `ps aux | grep cron_collector`
3. Manually run the collector to populate data: `python cron_collector.py`

### Charts Not Loading
1. Check internet connection (Plotly loads from CDN)
2. Verify browser supports JavaScript
3. Check browser console for any errors

## Development

The application runs in debug mode by default. For production deployment, consider:
- Setting `debug=False`
- Using a production WSGI server like Gunicorn
- Adding proper error handling and logging
- Implementing user authentication if needed

## Files

- `cron_dash_web.py` - Main Flask application
- `~/.cron_dash/ladder.db` - SQLite database with cron execution data
- `README_cron_dashboard.md` - This documentation file
