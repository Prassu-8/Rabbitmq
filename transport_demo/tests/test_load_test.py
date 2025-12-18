from __future__ import annotations

import sqlite3

from transport_demo import db
from transport_demo.load_test import run_scenario


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db.init_db(conn)
    return conn


def test_run_scenario_returns_metrics():
    conn = _conn()
    result = run_scenario(conn, duration_sec=1, ride_rate_per_minute=2, acceptance_rate=0.0)
    assert result["ticks"] >= 1
    assert "summary" in result
