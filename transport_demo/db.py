"""SQLite helper utilities."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

#from transport_demo import DB_PATH
from .config import DB_PATH



def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session(db_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS transport_sla_profile (
            sla_id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_code TEXT NOT NULL,
            area_code TEXT NOT NULL,
            slot_start TEXT NOT NULL,
            slot_end TEXT NOT NULL,
            priority_tier TEXT NOT NULL,
            attempt_window_sec INTEGER NOT NULL,
            max_attempts INTEGER NOT NULL,
            cooldown_between_attempts_sec INTEGER NOT NULL,
            assign_before_slot_min INTEGER NOT NULL,
            target_delivery_window_min INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_sla_unique
        ON transport_sla_profile(city_code, area_code, slot_start, slot_end, priority_tier);

        CREATE TABLE IF NOT EXISTS rides (
            ride_id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_code TEXT NOT NULL,
            area_code TEXT NOT NULL,
            slot_start TEXT NOT NULL,
            slot_end TEXT NOT NULL,
            priority_tier TEXT NOT NULL,
            pickup_lat REAL,
            pickup_lng REAL,
            drop_lat REAL,
            drop_lng REAL,
            pickup_address TEXT,
            drop_address TEXT,
            load_type TEXT,
            load_weight_kg REAL,
            offered_rate REAL,
            retailer_id INTEGER,
            retailer_name TEXT,
            retailer_phone TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ride_allocations (
            allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ride_id INTEGER NOT NULL,
            attempt_no INTEGER NOT NULL,
            max_attempts INTEGER NOT NULL,
            attempt_start_at TEXT,
            attempt_expires_at TEXT,
            next_attempt_not_before TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (ride_id) REFERENCES rides(ride_id)
        );

        CREATE TABLE IF NOT EXISTS dead_letter_messages (
            dlx_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ride_id INTEGER NOT NULL,
            attempt_no INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (ride_id) REFERENCES rides(ride_id)
       );
                       """ 
    )
