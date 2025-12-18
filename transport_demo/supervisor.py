"""Supervisor loop that drives allocation attempts.

Pulls rides via :mod:`ride_repository`, decides next actions per SLA rules,
and publishes `offer.create` messages through
:class:`transport_demo.rabbitmq_client.RabbitMQClient`. Coordinated with the
offer worker in :mod:`transport_demo.offer_worker`.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional, Sequence, Tuple

import sqlite3

from .config import SUPERVISOR_POLL_INTERVAL_SEC
from .models import AllocationStatus, Ride, RideAllocation, RideStatus, SLAProfile, SupervisorDecision
from .rabbitmq_client import RabbitMQClient
from . import ride_repository, sla_repository

LOGGER = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def decide_next_action(
    ride: Ride,
    allocation: RideAllocation,
    sla: SLAProfile,
    now: Optional[datetime] = None,
) -> SupervisorDecision:
    now = now or _now()
    cutoff = ride.slot_start_dt() - timedelta(minutes=sla.assign_before_slot_min)
    if ride.status in {RideStatus.NO_TAKERS.value, RideStatus.ACCEPTED.value}:
        return SupervisorDecision.NO_ACTION

    if allocation.status == AllocationStatus.NOT_STARTED.value:
        return (
            SupervisorDecision.START_FIRST_ATTEMPT
            if now < cutoff
            else SupervisorDecision.MARK_NO_TAKERS
        )

    if allocation.status in {
        AllocationStatus.PENDING.value,
        AllocationStatus.SENT.value,
    }:
        expires_at = allocation.attempt_expires_dt()
        if expires_at and now <= expires_at:
            return SupervisorDecision.STILL_ACTIVE_WAIT
        if allocation.attempt_no >= allocation.max_attempts or now >= cutoff:
            return SupervisorDecision.MARK_NO_TAKERS
        next_allowed = allocation.next_attempt_not_before_dt()
        if next_allowed and now < next_allowed:
            return SupervisorDecision.WAITING_COOLDOWN
        return SupervisorDecision.START_NEXT_ATTEMPT

    if allocation.status == AllocationStatus.WAITING_COOLDOWN.value:
        if allocation.attempt_no >= allocation.max_attempts or now >= cutoff:
            return SupervisorDecision.MARK_NO_TAKERS
        next_allowed = allocation.next_attempt_not_before_dt()
        if next_allowed and now < next_allowed:
            return SupervisorDecision.WAITING_COOLDOWN
        return SupervisorDecision.START_NEXT_ATTEMPT

    if allocation.status in {AllocationStatus.ACCEPTED.value, AllocationStatus.NO_TAKERS.value}:
        return SupervisorDecision.NO_ACTION

    return SupervisorDecision.NO_ACTION


def _start_attempt(
    conn: sqlite3.Connection,
    rabbitmq: RabbitMQClient,
    ride: Ride,
    allocation: RideAllocation,
    sla: SLAProfile,
    now: Optional[datetime],
    is_first: bool,
) -> None:
    now = now or _now()
    attempt_no = 1 if is_first else allocation.attempt_no + 1
    attempt_start = now.isoformat()
    attempt_expires = (now + timedelta(seconds=sla.attempt_window_sec)).isoformat()
    next_attempt_not_before = (
        datetime.fromisoformat(attempt_expires)
        + timedelta(seconds=sla.cooldown_between_attempts_sec)
    ).isoformat()

    ride_repository.update_allocation(
        conn,
        allocation.allocation_id,
        attempt_no=attempt_no,
        attempt_start_at=attempt_start,
        attempt_expires_at=attempt_expires,
        next_attempt_not_before=next_attempt_not_before,
        status=AllocationStatus.PENDING.value,
    )
    ride_repository.mark_ride_allocating(conn, ride.ride_id)

    LOGGER.info("Publishing offer.create for ride %s attempt %s", ride.ride_id, attempt_no)
    rabbitmq.publish_offer_create(
        ride_id=ride.ride_id,
        attempt_no=attempt_no,
        city=ride.city_code,
        area=ride.area_code,
    )


def apply_decision(
    conn: sqlite3.Connection,
    rabbitmq: RabbitMQClient,
    ride: Ride,
    allocation: RideAllocation,
    sla: SLAProfile,
    decision: SupervisorDecision,
    now: Optional[datetime] = None,
) -> None:
    if decision == SupervisorDecision.START_FIRST_ATTEMPT:
        _start_attempt(conn, rabbitmq, ride, allocation, sla, now, is_first=True)
        return
    if decision == SupervisorDecision.START_NEXT_ATTEMPT:
        _start_attempt(conn, rabbitmq, ride, allocation, sla, now, is_first=False)
        return
    if decision == SupervisorDecision.WAITING_COOLDOWN:
        ride_repository.update_allocation(
            conn,
            allocation.allocation_id,
            status=AllocationStatus.WAITING_COOLDOWN.value,
        )
        return
    if decision == SupervisorDecision.MARK_NO_TAKERS:
        ride_repository.mark_allocation_no_takers(conn, allocation.allocation_id)
        ride_repository.mark_ride_no_takers(conn, ride.ride_id)
        ride_repository.record_dead_letter(
            conn,
            ride.ride_id,
            allocation.attempt_no,
            "NO_TAKERS",
        )
        return
    # STILL_ACTIVE_WAIT and NO_ACTION intentionally fall through.


def process_allocations(
    conn: sqlite3.Connection,
    rabbitmq: RabbitMQClient,
    now: Optional[datetime] = None,
) -> List[Tuple[Ride, RideAllocation, SupervisorDecision]]:
    processed: List[Tuple[Ride, RideAllocation, SupervisorDecision]] = []
    for ride, allocation in ride_repository.get_allocations_needing_action(conn):
        sla = sla_repository.get_sla_for(
            conn,
            ride.city_code,
            ride.area_code,
            ride.slot_start,
            ride.priority_tier,
        )
        if not sla:
            LOGGER.warning(
                "Missing SLA for ride %s - marking as no takers", ride.ride_id
            )
            ride_repository.mark_allocation_no_takers(conn, allocation.allocation_id)
            ride_repository.mark_ride_no_takers(conn, ride.ride_id)
            ride_repository.record_dead_letter(
                conn, ride.ride_id, allocation.attempt_no, "MISSING_SLA"
            )
            continue
        decision = decide_next_action(ride, allocation, sla, now=now)
        apply_decision(conn, rabbitmq, ride, allocation, sla, decision, now=now)
        processed.append((ride, allocation, decision))
    return processed


def run_supervisor_loop(
    conn_factory,
    rabbitmq: RabbitMQClient,
    poll_interval: int = SUPERVISOR_POLL_INTERVAL_SEC,
    stop_event=None,
) -> None:
    try:
        rabbitmq.connect()
    except Exception:
        LOGGER.exception("Failed to connect to RabbitMQ")
        raise

    while True:
        with conn_factory() as conn:
            process_allocations(conn, rabbitmq)
            conn.commit()
        if stop_event and stop_event.is_set():
            break
        time.sleep(poll_interval)
