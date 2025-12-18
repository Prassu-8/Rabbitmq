from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlite3

from transport_demo import db, ride_repository, sla_repository
from transport_demo.sim_runner import run_step, seed_environment


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db.init_db(conn)
    return conn


def _future_slot():
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    slot_start = tomorrow.replace(hour=4, minute=0, second=0, microsecond=0).isoformat()
    slot_end = tomorrow.replace(hour=6, minute=0, second=0, microsecond=0).isoformat()
    now = tomorrow.replace(hour=1, minute=0, second=0, microsecond=0)
    return slot_start, slot_end, now


def test_run_step_generates_summary_and_live_offers():
    conn = _conn()
    seed_environment(conn, ride_count=0)
    slot_start, slot_end, now = _future_slot()
    ride_id = ride_repository.create_ride(
        conn,
        city_code="DELHI",
        area_code="NORTH_DELHI",
        slot_start=slot_start,
        slot_end=slot_end,
        priority_tier="STANDARD",
    )
    ride_repository.create_initial_allocation_for_ride(conn, ride_id, max_attempts=3)

    result = run_step(conn, acceptance_rate=0.0, now=now)
    assert "summary" in result
    assert result["summary"]["rides"].get("ALLOCATING") == 1
    assert result["live_offers"][0]["ride_id"] == ride_id


def test_run_step_can_accept_when_probability_high():
    conn = _conn()
    seed_environment(conn, ride_count=0)
    slot_start, slot_end, now = _future_slot()
    ride_id = ride_repository.create_ride(
        conn,
        city_code="DELHI",
        area_code="NORTH_DELHI",
        slot_start=slot_start,
        slot_end=slot_end,
        priority_tier="STANDARD",
    )
    ride_repository.create_initial_allocation_for_ride(conn, ride_id, max_attempts=3)

    result = run_step(conn, acceptance_rate=1.0, now=now)
    assert result["summary"]["rides"].get("ACCEPTED") == 1
