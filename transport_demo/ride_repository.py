"""Repository helpers for rides and allocations."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import sqlite3

from .models import AllocationStatus, Ride, RideAllocation, RideStatus


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_ride(row: sqlite3.Row) -> Ride:
    return Ride(
        ride_id=row["ride_id"],
        city_code=row["city_code"],
        area_code=row["area_code"],
        slot_start=row["slot_start"],
        slot_end=row["slot_end"],
        priority_tier=row["priority_tier"],
        pickup_lat=row["pickup_lat"],
        pickup_lng=row["pickup_lng"],
        drop_lat=row["drop_lat"],
        drop_lng=row["drop_lng"],
        pickup_address=row["pickup_address"],
        drop_address=row["drop_address"],
        load_type=row["load_type"],
        load_weight_kg=row["load_weight_kg"],
        offered_rate=row["offered_rate"],
        retailer_id=row["retailer_id"],
        retailer_name=row["retailer_name"],
        retailer_phone=row["retailer_phone"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_allocation(row: sqlite3.Row) -> RideAllocation:
    return RideAllocation(
        allocation_id=row["allocation_id"],
        ride_id=row["ride_id"],
        attempt_no=row["attempt_no"],
        max_attempts=row["max_attempts"],
        attempt_start_at=row["attempt_start_at"],
        attempt_expires_at=row["attempt_expires_at"],
        next_attempt_not_before=row["next_attempt_not_before"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def create_ride(
    conn: sqlite3.Connection,
    city_code: str,
    area_code: str,
    slot_start: str,
    slot_end: str,
    priority_tier: str,
    pickup_lat: Optional[float] = None,
    pickup_lng: Optional[float] = None,
    drop_lat: Optional[float] = None,
    drop_lng: Optional[float] = None,
    pickup_address: Optional[str] = None,
    drop_address: Optional[str] = None,
    load_type: Optional[str] = None,
    load_weight_kg: Optional[float] = None,
    offered_rate: Optional[float] = None,
    retailer_id: Optional[int] = None,
    retailer_name: Optional[str] = None,
    retailer_phone: Optional[str] = None,
    status: RideStatus = RideStatus.NEW,
) -> int:
    now = _utcnow()
    cursor = conn.execute(
        """
        INSERT INTO rides (
            city_code,
            area_code,
            slot_start,
            slot_end,
            priority_tier,
            pickup_lat,
            pickup_lng,
            drop_lat,
            drop_lng,
            pickup_address,
            drop_address,
            load_type,
            load_weight_kg,
            offered_rate,
            retailer_id,
            retailer_name,
            retailer_phone,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            city_code,
            area_code,
            slot_start,
            slot_end,
            priority_tier,
            pickup_lat,
            pickup_lng,
            drop_lat,
            drop_lng,
            pickup_address,
            drop_address,
            load_type,
            load_weight_kg,
            offered_rate,
            retailer_id,
            retailer_name,
            retailer_phone,
            status.value,
            now,
            now,
        ),
    )
    return int(cursor.lastrowid)


def create_initial_allocation_for_ride(
    conn: sqlite3.Connection,
    ride_id: int,
    max_attempts: int,
) -> int:
    now = _utcnow()
    cursor = conn.execute(
        """
        INSERT INTO ride_allocations (
            ride_id,
            attempt_no,
            max_attempts,
            attempt_start_at,
            attempt_expires_at,
            next_attempt_not_before,
            status,
            created_at,
            updated_at
        ) VALUES (?, 0, ?, NULL, NULL, NULL, ?, ?, ?)
        """,
        (ride_id, max_attempts, AllocationStatus.NOT_STARTED.value, now, now),
    )
    return int(cursor.lastrowid)


def get_ride_by_id(conn: sqlite3.Connection, ride_id: int) -> Optional[Ride]:
    row = conn.execute("SELECT * FROM rides WHERE ride_id = ?", (ride_id,)).fetchone()
    return _row_to_ride(row) if row else None


def get_allocation_by_ride_id(conn: sqlite3.Connection, ride_id: int) -> Optional[RideAllocation]:
    row = conn.execute(
        "SELECT * FROM ride_allocations WHERE ride_id = ? ORDER BY allocation_id DESC LIMIT 1",
        (ride_id,),
    ).fetchone()
    return _row_to_allocation(row) if row else None


def get_allocations_needing_action(
    conn: sqlite3.Connection,
) -> List[Tuple[Ride, RideAllocation]]:
    rows = conn.execute(
        """
        SELECT ra.*
        FROM ride_allocations ra
        JOIN rides r ON r.ride_id = ra.ride_id
        WHERE r.status IN (?, ?)
          AND ra.status IN (?, ?, ?, ?)
        ORDER BY ra.updated_at ASC
        """,
        (
            RideStatus.NEW.value,
            RideStatus.ALLOCATING.value,
            AllocationStatus.NOT_STARTED.value,
            AllocationStatus.PENDING.value,
            AllocationStatus.SENT.value,
            AllocationStatus.WAITING_COOLDOWN.value,
        ),
    ).fetchall()

    allocations: List[Tuple[Ride, RideAllocation]] = []
    for row in rows:
        ride = get_ride_by_id(conn, row["ride_id"])
        if not ride:
            continue
        allocation = _row_to_allocation(row)
        allocations.append((ride, allocation))
    return allocations


def update_allocation(conn: sqlite3.Connection, allocation_id: int, **fields: str) -> None:
    if not fields:
        return
    fields["updated_at"] = _utcnow()
    assignments = ", ".join(f"{key} = ?" for key in fields.keys())
    conn.execute(
        f"UPDATE ride_allocations SET {assignments} WHERE allocation_id = ?",
        (*fields.values(), allocation_id),
    )


def mark_allocation_sent(conn: sqlite3.Connection, allocation_id: int) -> None:
    update_allocation(conn, allocation_id, status=AllocationStatus.SENT.value)


def mark_allocation_no_takers(conn: sqlite3.Connection, allocation_id: int) -> None:
    update_allocation(conn, allocation_id, status=AllocationStatus.NO_TAKERS.value)


def mark_ride_no_takers(conn: sqlite3.Connection, ride_id: int) -> None:
    conn.execute(
        "UPDATE rides SET status = ?, updated_at = ? WHERE ride_id = ?",
        (RideStatus.NO_TAKERS.value, _utcnow(), ride_id),
    )


def mark_ride_allocating(conn: sqlite3.Connection, ride_id: int) -> None:
    conn.execute(
        "UPDATE rides SET status = ?, updated_at = ? WHERE ride_id = ?",
        (RideStatus.ALLOCATING.value, _utcnow(), ride_id),
    )


def mark_ride_new(conn: sqlite3.Connection, ride_id: int) -> None:
    conn.execute(
        "UPDATE rides SET status = ?, updated_at = ? WHERE ride_id = ?",
        (RideStatus.NEW.value, _utcnow(), ride_id),
    )


def mark_allocation_accepted(conn: sqlite3.Connection, allocation_id: int) -> None:
    update_allocation(conn, allocation_id, status=AllocationStatus.ACCEPTED.value)


def mark_ride_accepted(conn: sqlite3.Connection, ride_id: int) -> None:
    conn.execute(
        "UPDATE rides SET status = ?, updated_at = ? WHERE ride_id = ?",
        (RideStatus.ACCEPTED.value, _utcnow(), ride_id),
    )


def list_live_offers(conn: sqlite3.Connection) -> List[dict]:
    """Return rides joined with allocations for driver UI consumption."""
    rows = conn.execute(
        """
        SELECT r.*, ra.attempt_no, ra.status AS allocation_status
        FROM ride_allocations ra
        JOIN rides r ON r.ride_id = ra.ride_id
        WHERE ra.status IN (?, ?)
        ORDER BY ra.updated_at DESC
        """,
        (AllocationStatus.PENDING.value, AllocationStatus.SENT.value),
    ).fetchall()

    offers: List[dict] = []
    for row in rows:
        offers.append(
            {
                "ride_id": row["ride_id"],
                "attempt_no": row["attempt_no"],
                "status": row["allocation_status"],
                "slot_start": row["slot_start"],
                "slot_end": row["slot_end"],
                "pickup_address": row["pickup_address"],
                "drop_address": row["drop_address"],
                "pickup_lat": row["pickup_lat"],
                "pickup_lng": row["pickup_lng"],
                "drop_lat": row["drop_lat"],
                "drop_lng": row["drop_lng"],
                "load_type": row["load_type"],
                "load_weight_kg": row["load_weight_kg"],
                "offered_rate": row["offered_rate"],
            }
        )
    return offers


def get_recent_attempts_summary(conn: sqlite3.Connection, window_minutes: int) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    attempts = conn.execute(
        """
        SELECT status, COUNT(*) AS count
        FROM ride_allocations
        WHERE attempt_start_at IS NOT NULL
          AND attempt_start_at >= ?
        GROUP BY status
        """,
        (since,),
    ).fetchall()
    attempts_by_status = {row["status"]: row["count"] for row in attempts}
    attempts_started = sum(attempts_by_status.values())

    rides_accepted = conn.execute(
        "SELECT COUNT(*) FROM rides WHERE status = ? AND updated_at >= ?",
        (RideStatus.ACCEPTED.value, since),
    ).fetchone()[0]
    rides_no_takers = conn.execute(
        "SELECT COUNT(*) FROM rides WHERE status = ? AND updated_at >= ?",
        (RideStatus.NO_TAKERS.value, since),
    ).fetchone()[0]

    return {
        "window_min": window_minutes,
        "attempts_started": attempts_started,
        "attempts_by_status": attempts_by_status,
        "rides_accepted": rides_accepted,
        "rides_no_takers": rides_no_takers,
    }


def get_pending_manual_rides(conn: sqlite3.Connection) -> List[dict]:
    now_iso = _utcnow()
    rows = conn.execute(
        """
        SELECT *
        FROM rides
        WHERE status = ?
          AND slot_start >= ?
        ORDER BY slot_start ASC
        """,
        (RideStatus.NO_TAKERS.value, now_iso),
    ).fetchall()
    pending: List[dict] = []
    for row in rows:
        pending.append(
            {
                "ride_id": row["ride_id"],
                "city_code": row["city_code"],
                "area_code": row["area_code"],
                "slot_start": row["slot_start"],
                "slot_end": row["slot_end"],
                "pickup_address": row["pickup_address"],
                "drop_address": row["drop_address"],
                "load_type": row["load_type"],
                "load_weight_kg": row["load_weight_kg"],
                "offered_rate": row["offered_rate"],
                "retailer_name": row["retailer_name"],
                "retailer_phone": row["retailer_phone"],
            }
        )
    return pending


def record_dead_letter(
    conn: sqlite3.Connection, ride_id: int, attempt_no: int, reason: str
) -> None:
    conn.execute(
        """
        INSERT INTO dead_letter_messages (ride_id, attempt_no, reason, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (ride_id, attempt_no, reason, _utcnow()),
    )


def list_dead_letters(conn: sqlite3.Connection) -> List[dict]:
    rows = conn.execute(
        "SELECT * FROM dead_letter_messages ORDER BY created_at DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def clear_dead_letters_for_ride(conn: sqlite3.Connection, ride_id: int) -> None:
    conn.execute("DELETE FROM dead_letter_messages WHERE ride_id = ?", (ride_id,))


def reset_allocation_for_retry(conn: sqlite3.Connection, ride_id: int) -> bool:
    allocation = get_allocation_by_ride_id(conn, ride_id)
    if not allocation:
        return False
    update_allocation(
        conn,
        allocation.allocation_id,
        attempt_no=0,
        attempt_start_at=None,
        attempt_expires_at=None,
        next_attempt_not_before=None,
        status=AllocationStatus.NOT_STARTED.value,
    )
    mark_ride_new(conn, ride_id)
    return True
