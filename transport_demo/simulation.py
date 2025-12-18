"""Helper utilities to simulate supervisor/worker cycles with configurable acceptance rates."""
from __future__ import annotations

import random
from datetime import datetime
from typing import List, Optional

import sqlite3

#import ride_repository
from .config import SIM_ACCEPTANCE_RATE
from .offer_worker import handle_offer_create_message
from .supervisor import process_allocations


class _SimulationRabbit:
    """In-memory RabbitMQ stub that feeds messages directly to the offer worker."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        acceptance_rate: float,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.conn = conn
        self.acceptance_rate = acceptance_rate
        self.rng = rng or random.Random()
        self.messages: List[dict] = []

    def publish_offer_create(self, ride_id: int, attempt_no: int, city: str, area: str):
        payload = {
            "ride_id": ride_id,
            "attempt_no": attempt_no,
            "city": city,
            "area": area,
        }
        self.messages.append(payload)
        handle_offer_create_message(
            self.conn,
            payload,
            acceptance_rate=self.acceptance_rate,
            rng=self.rng,
        )


def simulate_tick(
    conn: sqlite3.Connection,
    now: datetime,
    acceptance_rate: float = SIM_ACCEPTANCE_RATE,
    rng: Optional[random.Random] = None,
):
    """Run one supervisor tick and immediately process any offers via the worker."""
    rabbit = _SimulationRabbit(conn, acceptance_rate, rng)
    return process_allocations(conn, rabbit, now=now)


def summarize_statuses(conn: sqlite3.Connection) -> dict:
    rides = conn.execute("SELECT status, COUNT(*) AS count FROM rides GROUP BY status").fetchall()
    allocations = conn.execute(
        "SELECT status, COUNT(*) AS count FROM ride_allocations GROUP BY status"
    ).fetchall()
    return {
        "rides": {row["status"]: row["count"] for row in rides},
        "allocations": {row["status"]: row["count"] for row in allocations},
    }
