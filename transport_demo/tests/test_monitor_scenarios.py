from __future__ import annotations

from datetime import datetime, timezone

import sqlite3

from transport_demo import db
from transport_demo.monitor_scenarios import run_scenario_metrics


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db.init_db(conn)
    return conn


def test_run_scenario_metrics(monkeypatch):
    conn = _conn()

    class FakeProcess:
        def cpu_percent(self, interval=None):
            return 10.0

        def memory_info(self):
            class Info:
                rss = 1234567

            return Info()

    monkeypatch.setattr("psutil.Process", lambda: FakeProcess())
    monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 10.0)

    result = run_scenario_metrics(conn, ["delhi_steady"], steps=1, acceptance_rate=0.0, tick_sleep=0)
    assert "summary" in result
    assert result["cpu_avg"] == 10.0
