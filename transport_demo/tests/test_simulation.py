from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlite3

from transport_demo import db
from transport_demo import ride_repository, sla_repository
from transport_demo.simulation import simulate_tick, summarize_statuses


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db.init_db(conn)
    return conn


def _seed_ride(conn):
    sla_repository.seed_default_sla(conn)
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    slot_start = tomorrow.replace(hour=4, minute=0, second=0, microsecond=0).isoformat()
    slot_end = tomorrow.replace(hour=6, minute=0, second=0, microsecond=0).isoformat()
    ride_id = ride_repository.create_ride(
        conn,
        city_code="DELHI",
        area_code="NORTH_DELHI",
        slot_start=slot_start,
        slot_end=slot_end,
        priority_tier="STANDARD",
    )
    ride_repository.create_initial_allocation_for_ride(conn, ride_id, max_attempts=3)
    return ride_id


def test_simulate_tick_accepts_with_high_probability():
    conn = _conn()
    _seed_ride(conn)
    now = datetime.now(timezone.utc)
    simulate_tick(conn, now=now, acceptance_rate=1.0)
    summary = summarize_statuses(conn)
    assert summary["rides"].get("ACCEPTED") == 1
    assert summary["allocations"].get("ACCEPTED") == 1


def test_simulate_tick_without_acceptance_keeps_allocating():
    conn = _conn()
    _seed_ride(conn)
    now = datetime.now(timezone.utc)
    simulate_tick(conn, now=now, acceptance_rate=0.0)
    summary = summarize_statuses(conn)
    assert summary["rides"].get("ALLOCATING") == 1
    assert summary["allocations"].get("SENT") == 1
