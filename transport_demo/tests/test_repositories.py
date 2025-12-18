from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlite3

from transport_demo import db
from transport_demo import ride_repository
from transport_demo.models import AllocationStatus, RideStatus


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db.init_db(conn)
    return conn


def test_create_ride_and_allocation_crud():
    conn = _conn()
    slot_start = datetime(2024, 1, 1, 4, 0, tzinfo=timezone.utc).isoformat()
    slot_end = datetime(2024, 1, 1, 6, 0, tzinfo=timezone.utc).isoformat()
    ride_id = ride_repository.create_ride(
        conn,
        city_code="DELHI",
        area_code="NORTH_DELHI",
        slot_start=slot_start,
        slot_end=slot_end,
        priority_tier="STANDARD",
    )
    allocation_id = ride_repository.create_initial_allocation_for_ride(conn, ride_id, max_attempts=3)

    allocation = ride_repository.get_allocation_by_ride_id(conn, ride_id)
    assert allocation and allocation.allocation_id == allocation_id
    assert allocation.status == AllocationStatus.NOT_STARTED.value

    ride_repository.mark_ride_allocating(conn, ride_id)
    ride_repository.mark_allocation_sent(conn, allocation_id)
    ride_repository.mark_allocation_no_takers(conn, allocation_id)
    ride_repository.mark_ride_no_takers(conn, ride_id)

    allocation = ride_repository.get_allocation_by_ride_id(conn, ride_id)
    ride = ride_repository.get_ride_by_id(conn, ride_id)
    assert allocation.status == AllocationStatus.NO_TAKERS.value
    assert ride.status == RideStatus.NO_TAKERS.value


def test_list_live_offers_returns_pending_allocations():
    conn = _conn()
    slot_start = datetime(2024, 1, 1, 4, 0, tzinfo=timezone.utc).isoformat()
    slot_end = datetime(2024, 1, 1, 6, 0, tzinfo=timezone.utc).isoformat()
    ride_id = ride_repository.create_ride(
        conn,
        city_code="DELHI",
        area_code="NORTH_DELHI",
        slot_start=slot_start,
        slot_end=slot_end,
        priority_tier="STANDARD",
        pickup_address="Test Pickup",
        drop_address="Test Drop",
        load_type="Fruits",
        offered_rate=500.0,
    )
    allocation_id = ride_repository.create_initial_allocation_for_ride(conn, ride_id, max_attempts=3)
    ride_repository.update_allocation(conn, allocation_id, status=AllocationStatus.PENDING.value)

    offers = ride_repository.list_live_offers(conn)
    assert len(offers) == 1
    assert offers[0]["ride_id"] == ride_id
    assert offers[0]["pickup_address"] == "Test Pickup"


def test_recent_attempts_summary_counts_statuses():
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
    ts = datetime.now(timezone.utc).isoformat()
    ride_repository.update_allocation(
        conn,
        alloc_id,
        attempt_start_at=ts,
        status=AllocationStatus.PENDING.value,
    )
    conn.execute(
        "UPDATE rides SET status = ?, updated_at = ? WHERE ride_id = ?",
        (RideStatus.ACCEPTED.value, ts, ride_id),
    )

    second_ride = ride_repository.create_ride(
        conn,
        city_code="DELHI",
        area_code="NORTH_DELHI",
        slot_start=slot_start,
        slot_end=slot_end,
        priority_tier="STANDARD",
    )
    second_alloc = ride_repository.create_initial_allocation_for_ride(conn, second_ride, max_attempts=3)
    ride_repository.update_allocation(
        conn,
        second_alloc,
        attempt_start_at=ts,
        status=AllocationStatus.NO_TAKERS.value,
    )
    conn.execute(
        "UPDATE rides SET status = ?, updated_at = ? WHERE ride_id = ?",
        (RideStatus.NO_TAKERS.value, ts, second_ride),
    )

    summary = ride_repository.get_recent_attempts_summary(conn, window_minutes=10)
    assert summary["attempts_started"] == 2
    assert summary["attempts_by_status"][AllocationStatus.PENDING.value] == 1
    assert summary["attempts_by_status"][AllocationStatus.NO_TAKERS.value] == 1
    assert summary["rides_accepted"] == 1
    assert summary["rides_no_takers"] == 1


def test_get_pending_manual_rides_returns_future_no_takers():
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
        pickup_address="Okhla",
        drop_address="Lajpat",
        retailer_name="Gupta Store",
        retailer_phone="+91-9000000000",
    )
    ride_repository.mark_ride_no_takers(conn, ride_id)

    pending = ride_repository.get_pending_manual_rides(conn)
    assert len(pending) == 1
    entry = pending[0]
    assert entry["ride_id"] == ride_id
    assert entry["retailer_name"] == "Gupta Store"


def test_dead_letter_record_and_list():
    conn = _conn()
    slot_start = datetime(2024, 1, 1, 4, 0, tzinfo=timezone.utc).isoformat()
    slot_end = datetime(2024, 1, 1, 6, 0, tzinfo=timezone.utc).isoformat()
    ride_id = ride_repository.create_ride(
        conn,
        city_code="DELHI",
        area_code="NORTH_DELHI",
        slot_start=slot_start,
        slot_end=slot_end,
        priority_tier="STANDARD",
    )
    ride_repository.record_dead_letter(conn, ride_id, attempt_no=3, reason="NO_TAKERS")
    entries = ride_repository.list_dead_letters(conn)
    assert len(entries) == 1
    assert entries[0]["ride_id"] == ride_id
