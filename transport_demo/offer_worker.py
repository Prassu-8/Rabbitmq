"""Offer worker consumes offer.create messages and marks allocations as sent.

Works with :mod:`transport_demo.ride_repository` to update allocation state and
is typically launched via ``main_offer_worker`` alongside the supervisor.
"""
from __future__ import annotations

import logging
import random
from typing import Dict, Optional

import sqlite3

from . import ride_repository
from .config import SIM_ACCEPTANCE_RATE
from .rabbitmq_client import RabbitMQClient

LOGGER = logging.getLogger(__name__)


def handle_offer_create_message(
    conn: sqlite3.Connection,
    payload: Dict,
    acceptance_rate: float = SIM_ACCEPTANCE_RATE,
    rng: Optional[random.Random] = None,
) -> None:
    ride_id = int(payload["ride_id"])
    attempt_no = int(payload["attempt_no"])
    allocation = ride_repository.get_allocation_by_ride_id(conn, ride_id)
    if not allocation:
        LOGGER.warning("No allocation found for ride %s", ride_id)
        return
    if allocation.attempt_no != attempt_no:
        LOGGER.info(
            "Ignoring stale offer for ride %s attempt %s (current %s)",
            ride_id,
            attempt_no,
            allocation.attempt_no,
        )
        return
    ride_repository.mark_allocation_sent(conn, allocation.allocation_id)
    LOGGER.info("Marked ride %s attempt %s as SENT", ride_id, attempt_no)

    if acceptance_rate > 0:
        rng = rng or random.Random()
        if rng.random() <= acceptance_rate:
            LOGGER.info("Simulating acceptance for ride %s", ride_id)
            ride_repository.mark_allocation_accepted(conn, allocation.allocation_id)
            ride_repository.mark_ride_accepted(conn, ride_id)


def run_offer_worker(conn_factory, rabbitmq: RabbitMQClient) -> None:
    rabbitmq.connect()

    def _callback(payload: Dict) -> None:
        with conn_factory() as conn:
            handle_offer_create_message(conn, payload)
            conn.commit()

    rabbitmq.consume_offer_create(_callback)
