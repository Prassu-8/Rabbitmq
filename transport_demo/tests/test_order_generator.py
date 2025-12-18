from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlite3

from transport_demo import db, ride_repository
from transport_demo.order_generator import OrderGenerator, ScenarioConfig


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db.init_db(conn)
    return conn


def test_order_generator_spawns_per_interval():
    conn = _conn()
    config = ScenarioConfig(
        name="test",
        city_code="DELHI",
        area_code="NORTH_DELHI",
        spawn_interval_sec=0,
        batch_size=2,
    )
    generator = OrderGenerator(conn, [config])
    now = datetime.now(timezone.utc)
    spawned = generator.tick(now)
    assert spawned == 2
    total = conn.execute("SELECT COUNT(*) FROM rides").fetchone()[0]
    assert total == 2


def test_order_generator_respects_pause_cycle():
    conn = _conn()
    config = ScenarioConfig(
        name="intermittent",
        city_code="DELHI",
        area_code="NORTH_DELHI",
        spawn_interval_sec=1,
        batch_size=1,
        active_duration_sec=2,
        pause_duration_sec=5,
    )
    generator = OrderGenerator(conn, [config])
    now = datetime.now(timezone.utc)
    assert generator.tick(now) == 1
    # Next tick within active window but after interval should spawn again
    assert generator.tick(now + timedelta(seconds=1)) == 1
    # After active duration passes, generator pauses
    assert generator.tick(now + timedelta(seconds=3)) == 0
    # After pause duration, it resumes
    assert generator.tick(now + timedelta(seconds=8)) == 1
