from __future__ import annotations
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager

import sqlite3
from fastapi.testclient import TestClient

from transport_demo import db
from transport_demo import ride_repository
from transport_demo.api_dummy import app


def _setup_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    db.init_db(conn)
    return conn


def test_accept_offer_endpoint(monkeypatch):
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
    ride_repository.update_allocation(
        conn,
        alloc_id,
        attempt_no=1,
        status="PENDING",
    )
    ride_repository.mark_ride_allocating(conn, ride_id)
    conn.commit()

    @contextmanager
    def _override():
        yield conn

    monkeypatch.setattr("transport_demo.api_dummy.db.db_session", _override)
    client = TestClient(app)
    response = client.post("/offers/accept", json={"ride_id": ride_id, "attempt_no": 1})
    assert response.status_code == 200
    allocation = ride_repository.get_allocation_by_ride_id(conn, ride_id)
    ride = ride_repository.get_ride_by_id(conn, ride_id)
    assert allocation.status == "ACCEPTED"
    assert ride.status == "ACCEPTED"
