from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlite3

from transport_demo import db
from transport_demo import ride_repository, sla_repository
from transport_demo.models import AllocationStatus, RideStatus
from transport_demo.supervisor import process_allocations


class FakeRabbit:
    def __init__(self) -> None:
        self.messages = []

    def publish_offer_create(self, **payload):
        self.messages.append(payload)


def _connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db.init_db(conn)
    return conn


def test_process_allocations_starts_first_attempt_and_publishes():
    conn = _connection()
    sla_repository.seed_default_sla(conn)
    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    slot_start = (base + timedelta(hours=6)).isoformat()
    slot_end = (base + timedelta(hours=8)).isoformat()
    ride_id = ride_repository.create_ride(
        conn,
        city_code="DELHI",
        area_code="NORTH_DELHI",
        slot_start=slot_start,
        slot_end=slot_end,
        priority_tier="STANDARD",
    )
    ride_repository.create_initial_allocation_for_ride(conn, ride_id, max_attempts=3)

    rabbit = FakeRabbit()
    process_allocations(conn, rabbit, now=base + timedelta(hours=1))

    allocation = ride_repository.get_allocation_by_ride_id(conn, ride_id)
    assert allocation is not None
    assert allocation.status == AllocationStatus.PENDING.value
    assert allocation.attempt_no == 1
    assert rabbit.messages and rabbit.messages[0]["ride_id"] == ride_id
    ride = ride_repository.get_ride_by_id(conn, ride_id)
    assert ride.status == RideStatus.ALLOCATING.value


def test_allocation_without_sla_marked_no_takers():
    conn = _connection()
    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    slot_start = (base + timedelta(hours=6)).isoformat()
    slot_end = (base + timedelta(hours=8)).isoformat()
    ride_id = ride_repository.create_ride(
        conn,
        city_code="DELHI",
        area_code="SOUTH_DELHI",
        slot_start=slot_start,
        slot_end=slot_end,
        priority_tier="STANDARD",
    )
    ride_repository.create_initial_allocation_for_ride(conn, ride_id, max_attempts=3)

    rabbit = FakeRabbit()
    process_allocations(conn, rabbit, now=base + timedelta(hours=1))

    allocation = ride_repository.get_allocation_by_ride_id(conn, ride_id)
    ride = ride_repository.get_ride_by_id(conn, ride_id)
    assert allocation.status == AllocationStatus.NO_TAKERS.value
    assert ride.status == RideStatus.NO_TAKERS.value
    assert not rabbit.messages
    dead_letters = ride_repository.list_dead_letters(conn)
    assert dead_letters and dead_letters[0]["ride_id"] == ride_id
