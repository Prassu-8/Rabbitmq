"""SLA repository helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlite3

from .models import SLAProfile


DEFAULT_SLA = {
    "city_code": "DELHI",
    "area_code": "NORTH_DELHI",
    "slot_start": "04:00",
    "slot_end": "06:00",
    "priority_tier": "STANDARD",
    "attempt_window_sec": 60,
    "max_attempts": 3,
    "cooldown_between_attempts_sec": 180,
    "assign_before_slot_min": 30,
    "target_delivery_window_min": 240,
}


def ensure_sla(conn: sqlite3.Connection, **kwargs) -> None:
    payload = {
        **DEFAULT_SLA,
        **kwargs,
    }
    payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    conn.execute(
        """
        INSERT OR IGNORE INTO transport_sla_profile (
            city_code,
            area_code,
            slot_start,
            slot_end,
            priority_tier,
            attempt_window_sec,
            max_attempts,
            cooldown_between_attempts_sec,
            assign_before_slot_min,
            target_delivery_window_min,
            is_active,
            created_at
        ) VALUES (:city_code, :area_code, :slot_start, :slot_end, :priority_tier,
                  :attempt_window_sec, :max_attempts, :cooldown_between_attempts_sec,
                  :assign_before_slot_min, :target_delivery_window_min, 1, :created_at)
        """,
        payload,
    )


def seed_default_sla(conn: sqlite3.Connection) -> None:
    ensure_sla(conn)


def _row_to_sla(row: sqlite3.Row) -> SLAProfile:
    return SLAProfile(
        sla_id=row["sla_id"],
        city_code=row["city_code"],
        area_code=row["area_code"],
        slot_start=row["slot_start"],
        slot_end=row["slot_end"],
        priority_tier=row["priority_tier"],
        attempt_window_sec=row["attempt_window_sec"],
        max_attempts=row["max_attempts"],
        cooldown_between_attempts_sec=row["cooldown_between_attempts_sec"],
        assign_before_slot_min=row["assign_before_slot_min"],
        target_delivery_window_min=row["target_delivery_window_min"],
        is_active=row["is_active"],
        created_at=row["created_at"],
    )


def get_sla_for(
    conn: sqlite3.Connection,
    city_code: str,
    area_code: str,
    slot_start_iso: str,
    priority_tier: str,
) -> Optional[SLAProfile]:
    slot_time = datetime.fromisoformat(slot_start_iso).strftime("%H:%M")
    row = conn.execute(
        """
        SELECT * FROM transport_sla_profile
        WHERE city_code = ?
          AND area_code = ?
          AND priority_tier = ?
          AND is_active = 1
          AND slot_start <= ?
          AND slot_end >= ?
        ORDER BY sla_id DESC
        LIMIT 1
        """,
        (city_code, area_code, priority_tier, slot_time, slot_time),
    ).fetchone()
    return _row_to_sla(row) if row else None
