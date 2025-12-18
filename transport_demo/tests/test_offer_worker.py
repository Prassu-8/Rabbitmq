from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import sqlite3

from transport_demo import db
from transport_demo import ride_repository
from transport_demo.offer_worker import handle_offer_create_message


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db.init_db(conn)
    return conn


def test_handle_offer_marks_sent_and_accepts_when_probability_high():
    conn = _conn()
    slot_start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    slot_end = (datetime.now(timezone.utc) + timedelta(days=1, hours=2)).isoformat()
    ride_id = ride_repository.create_ride(
        conn,
        city_code="DELHI",
        area_code="NORTH_DELHI",
        slot_start=slot_start,
        slot_end=slot_end,
        priority_tier="STANDARD",
    )
    alloc_id = ride_repository.create_initial_allocation_for_ride(conn, ride_id, max_attempts=3)
    ride_repository.update_allocation(
        conn,
        alloc_id,
        attempt_no=1,
        status="PENDING",
    )
    ride_repository.mark_ride_allocating(conn, ride_id)

    handle_offer_create_message(
        conn,
        {"ride_id": ride_id, "attempt_no": 1},
        acceptance_rate=1.0,
        rng=random.Random(0),
    )

    allocation = ride_repository.get_allocation_by_ride_id(conn, ride_id)
    ride = ride_repository.get_ride_by_id(conn, ride_id)
    assert allocation.status == "ACCEPTED"
    assert ride.status == "ACCEPTED"


def test_handle_offer_without_acceptance_leaves_pending():
    conn = _conn()
    slot_start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    slot_end = (datetime.now(timezone.utc) + timedelta(days=1, hours=2)).isoformat()
    ride_id = ride_repository.create_ride(
        conn,
        city_code="DELHI",
        area_code="NORTH_DELHI",
        slot_start=slot_start,
        slot_end=slot_end,
        priority_tier="STANDARD",
    )
    alloc_id = ride_repository.create_initial_allocation_for_ride(conn, ride_id, max_attempts=3)
    ride_repository.update_allocation(
        conn,
        alloc_id,
        attempt_no=1,
        status="PENDING",
    )
    ride_repository.mark_ride_allocating(conn, ride_id)

    handle_offer_create_message(
        conn,
        {"ride_id": ride_id, "attempt_no": 1},
        acceptance_rate=0.0,
    )

    allocation = ride_repository.get_allocation_by_ride_id(conn, ride_id)
    ride = ride_repository.get_ride_by_id(conn, ride_id)
    assert allocation.status == "SENT"
    assert ride.status == "ALLOCATING"
