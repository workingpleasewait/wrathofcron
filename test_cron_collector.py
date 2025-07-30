import pytest
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from cron_collector import CronCollector


@pytest.fixture
def sample_jsonl_file(tmp_path):
    """A fixture to create a sample JSONL file."""
    jsonl_content = '{"ts": "2023-01-01T12:00:00Z", "exit": 0, "msg": "Job 1"}\n{"ts": "2023-01-01T12:01:00Z", "exit": 1, "msg": "Job 2"}\n'
    jsonl_path = tmp_path / "ladder.jsonl"
    jsonl_path.write_text(jsonl_content)
    return jsonl_path


@pytest.fixture
def collector(tmp_path):
    """A fixture to create a CronCollector instance with temp paths."""
    db_path = tmp_path / "test.db"
    collector = CronCollector(db_path=db_path, log_level="DEBUG")
    collector.jsonl_path = tmp_path / "ladder.jsonl"
    collector.last_pos_file = tmp_path / "last_pos"
    return collector

def test_parse_jsonl_line(collector):
    """Unit test for the parse_jsonl_line method."""
    line = '{"ts": "2023-01-01T12:00:00Z", "exit": 0, "msg": "Test Job"}'
    entry = collector.parse_jsonl_line(line)
    assert entry is not None
    assert entry["timestamp"] == "2023-01-01T12:00:00Z"
    assert entry["exit_code"] == 0
    assert entry["message"] == "Test Job"
    # Check that parsed_at is a valid ISO-8601 timestamp
    datetime.fromisoformat(entry["parsed_at"])

def test_normalize_timestamp(collector):
    """Unit test for the normalize_timestamp method."""
    ts1 = "2023-10-27T10:00:00Z"
    ts2 = "2023-10-27 10:00:00"
    ts3 = "2023-10-27T10:00:00+02:00"
    
    assert collector.normalize_timestamp(ts1) == "2023-10-27T10:00:00+00:00"
    assert collector.normalize_timestamp(ts2) == "2023-10-27T10:00:00+00:00"
    assert collector.normalize_timestamp(ts3) == "2023-10-27T08:00:00+00:00"

def test_integration_run_collector(collector, sample_jsonl_file):
    """Integration test for running the collector on a sample file."""
    # Ensure the collector points to our sample file
    collector.jsonl_path = sample_jsonl_file
    
    # Run the collector to parse the sample file
    entries_processed = collector.parse_existing_entries()
    assert entries_processed == 2

    # Assert that the rows were inserted into the database
    with sqlite3.connect(collector.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cron_entries")
        row_count = cursor.fetchone()[0]
        assert row_count == 2
        
        # Also check that the data is correct
        cursor.execute("SELECT timestamp, exit_code, message FROM cron_entries ORDER BY timestamp")
        rows = cursor.fetchall()
        assert len(rows) == 2
        
        # Check first entry
        assert rows[0][0] == "2023-01-01T12:00:00+00:00"  # UTC normalized
        assert rows[0][1] == 0
        assert rows[0][2] == "Job 1"
        
        # Check second entry
        assert rows[1][0] == "2023-01-01T12:01:00+00:00"  # UTC normalized
        assert rows[1][1] == 1
        assert rows[1][2] == "Job 2"

    # Assert that the offset file was updated
    assert collector.last_pos_file.exists()
    with open(collector.last_pos_file, 'r') as f:
        last_pos = int(f.read().strip())
    assert last_pos > 0


