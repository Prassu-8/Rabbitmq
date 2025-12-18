from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlite3
from fastapi.testclient import TestClient

from transport_demo import db, ride_repository
from transport_demo.dashboard_api import app, get_db_conn


def _setup_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    db.init_db(conn)
    return conn


def test_dashboard_summary_endpoint(monkeypatch):
    conn = _setup_conn()
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
        status="PENDING",
    )
    conn.execute(
        "UPDATE rides SET status = ?, updated_at = ? WHERE ride_id = ?",
        ("ACCEPTED", ts, ride_id),
    )
    conn.commit()

    def _override():
        yield conn

    app.dependency_overrides[get_db_conn] = _override
    client = TestClient(app)
    response = client.get("/dashboard/summary?window_min=5")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["attempts_started"] == 1
    assert body["rides_accepted"] == 1


def test_pending_manual_endpoint(monkeypatch):
    conn = _setup_conn()
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
    )
    ride_repository.mark_ride_no_takers(conn, ride_id)
    conn.commit()

    def _override():
        yield conn

    app.dependency_overrides[get_db_conn] = _override
    client = TestClient(app)
    response = client.get("/dashboard/pending_manual")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["retailer_name"] == "Gupta Store"


def test_dead_letters_endpoint(monkeypatch):
    conn = _setup_conn()
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
    ride_repository.record_dead_letter(conn, ride_id, attempt_no=1, reason="NO_TAKERS")
    conn.commit()

    def _override():
        yield conn

    app.dependency_overrides[get_db_conn] = _override
    client = TestClient(app)
    response = client.get("/dashboard/dead_letters")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["ride_id"] == ride_id


def test_requeue_endpoint(monkeypatch):
    conn = _setup_conn()
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
    ride_repository.create_initial_allocation_for_ride(conn, ride_id, max_attempts=3)
    ride_repository.mark_allocation_no_takers(conn, ride_repository.get_allocation_by_ride_id(conn, ride_id).allocation_id)
    ride_repository.mark_ride_no_takers(conn, ride_id)
    ride_repository.record_dead_letter(conn, ride_id, attempt_no=1, reason="NO_TAKERS")
    conn.commit()

    def _override():
        yield conn

    app.dependency_overrides[get_db_conn] = _override
    client = TestClient(app)
    response = client.post(f"/dashboard/requeue/{ride_id}")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    allocation = ride_repository.get_allocation_by_ride_id(conn, ride_id)
    ride = ride_repository.get_ride_by_id(conn, ride_id)
    assert allocation.status == "NOT_STARTED"
    assert allocation.attempt_no == 0
    assert ride.status == "NEW"
