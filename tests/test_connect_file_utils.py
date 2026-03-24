"""Tests for local log formatting helpers in connect_file_utils."""

import gzip
import time
from pathlib import Path
from types import SimpleNamespace

from examples.connect_file_utils import rsync, show_gz_log


def test_show_gz_log_strips_html_and_decodes_entities(tmp_path, capsys):
    html = """
    <html><body>
      <h1>Job Log</h1>
      <pre>
        <font color=\"green\">INFO Hello &quot;World&quot;</font><br/>
        <font color=\"red\">ERROR Something failed</font>
      </pre>
      <script>console.log('hidden');</script>
    </body></html>
    """
    log_path = tmp_path / "sample.gz"
    with gzip.open(log_path, "wt", encoding="utf-8") as fh:
        fh.write(html)

    show_gz_log(str(log_path))
    out = capsys.readouterr().out

    assert "Job Log" in out
    assert 'INFO Hello "World"' in out
    assert "ERROR Something failed" in out
    assert "console.log" not in out


def test_rsync_recent_logs_skips_old_nested_log_entries(tmp_path, capsys):
    old_timestamp_ms = int((time.time() - 200000) * 1000)

    class FakeConnect:
        def __init__(self):
            self.client = SimpleNamespace()

        def get_files(self, path=None, project=None):
            if path in ("/", None):
                return [
                    {"path": "log", "timestamp": old_timestamp_ms, "fileEntries": []},
                    {"path": "archive", "timestamp": old_timestamp_ms, "fileEntries": []},
                ]
            if path == "log":
                return [{"path": "log/jobs", "timestamp": old_timestamp_ms, "fileEntries": []}]
            if path == "log/jobs":
                return [{"path": "log/jobs/2026-03-20", "timestamp": old_timestamp_ms, "fileEntries": []}]
            return []

    rsync(FakeConnect(), src="/", dest=str(tmp_path), dry_run=True, verbose=True, recent_logs=True)

    out = capsys.readouterr().out
    assert "Would create directory" in out
    assert "archive" in out
    assert "log/jobs" in out
    assert "Skipping old directory log/jobs/2026-03-20" in out


def test_rsync_recent_logs_allows_old_non_log_entries(tmp_path, capsys):
    old_timestamp_ms = int((time.time() - 200000) * 1000)

    class FakeConnect:
        def __init__(self):
            self.client = SimpleNamespace()

        def get_files(self, path=None, project=None):
            return [{"path": "recent.log.gz", "timestamp": old_timestamp_ms}]

    rsync(FakeConnect(), src="/", dest=str(tmp_path), dry_run=True, verbose=True, recent_logs=True)

    out = capsys.readouterr().out
    assert "recent.log.gz" in out
    assert "Skipping old" not in out


def test_rsync_recent_logs_allows_recent_nested_log_entries(tmp_path, capsys):
    recent_timestamp_ms = int((time.time() - 60) * 1000)

    class FakeConnect:
        def __init__(self):
            self.client = SimpleNamespace()

        def get_files(self, path=None, project=None):
            return [{"path": "log/jobs/2026-03-23/run.gz", "timestamp": recent_timestamp_ms}]

    rsync(FakeConnect(), src="/", dest=str(tmp_path), dry_run=True, verbose=True, recent_logs=True)

    out = capsys.readouterr().out
    assert "log/jobs/2026-03-23/run.gz" in out
    assert "Skipping old" not in out
