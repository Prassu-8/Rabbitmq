from __future__ import annotations

from datetime import datetime, timedelta, timezone

from transport_demo.models import (
    AllocationStatus,
    Ride,
    RideAllocation,
    RideStatus,
    SLAProfile,
    SupervisorDecision,
)
from transport_demo.supervisor import decide_next_action


BASE_TIME = datetime(2024, 1, 1, 2, 0, tzinfo=timezone.utc)


def _ride(slot_start: datetime) -> Ride:
    return Ride(
        ride_id=1,
        city_code="DELHI",
        area_code="NORTH_DELHI",
        slot_start=slot_start.isoformat(),
        slot_end=(slot_start + timedelta(hours=2)).isoformat(),
        priority_tier="STANDARD",
        pickup_lat=None,
        pickup_lng=None,
        drop_lat=None,
        drop_lng=None,
        pickup_address=None,
        drop_address=None,
        load_type=None,
        load_weight_kg=None,
        offered_rate=None,
        retailer_id=None,
        retailer_name=None,
        retailer_phone=None,
        status=RideStatus.NEW.value,
        created_at=BASE_TIME.isoformat(),
        updated_at=BASE_TIME.isoformat(),
    )


def _allocation(status: str, attempt_no: int = 0, expires: datetime | None = None, next_allowed: datetime | None = None) -> RideAllocation:
    return RideAllocation(
        allocation_id=1,
        ride_id=1,
        attempt_no=attempt_no,
        max_attempts=3,
        attempt_start_at=BASE_TIME.isoformat(),
        attempt_expires_at=expires.isoformat() if expires else None,
        next_attempt_not_before=next_allowed.isoformat() if next_allowed else None,
        status=status,
        created_at=BASE_TIME.isoformat(),
        updated_at=BASE_TIME.isoformat(),
    )


def _sla() -> SLAProfile:
    return SLAProfile(
        sla_id=1,
        city_code="DELHI",
        area_code="NORTH_DELHI",
        slot_start="04:00",
        slot_end="06:00",
        priority_tier="STANDARD",
        attempt_window_sec=60,
        max_attempts=3,
        cooldown_between_attempts_sec=180,
        assign_before_slot_min=30,
        target_delivery_window_min=120,
        is_active=1,
        created_at=BASE_TIME.isoformat(),
    )


def test_not_started_before_deadline_starts_first_attempt():
    ride = _ride(slot_start=BASE_TIME + timedelta(hours=2))
    allocation = _allocation(AllocationStatus.NOT_STARTED.value)
    decision = decide_next_action(ride, allocation, _sla(), now=BASE_TIME + timedelta(minutes=10))
    assert decision == SupervisorDecision.START_FIRST_ATTEMPT


def test_not_started_after_deadline_marks_no_takers():
    ride = _ride(slot_start=BASE_TIME + timedelta(minutes=25))
    allocation = _allocation(AllocationStatus.NOT_STARTED.value)
    decision = decide_next_action(ride, allocation, _sla(), now=BASE_TIME + timedelta(minutes=10))
    assert decision == SupervisorDecision.MARK_NO_TAKERS


def test_pending_within_attempt_window_waits():
    ride = _ride(slot_start=BASE_TIME + timedelta(hours=2))
    allocation = _allocation(
        AllocationStatus.PENDING.value,
        attempt_no=1,
        expires=BASE_TIME + timedelta(minutes=1),
    )
    decision = decide_next_action(ride, allocation, _sla(), now=BASE_TIME + timedelta(seconds=30))
    assert decision == SupervisorDecision.STILL_ACTIVE_WAIT


def test_waiting_can_start_next_attempt_after_cooldown():
    ride = _ride(slot_start=BASE_TIME + timedelta(hours=2))
    allocation = _allocation(
        AllocationStatus.WAITING_COOLDOWN.value,
        attempt_no=1,
        next_allowed=BASE_TIME + timedelta(minutes=5),
    )
    decision = decide_next_action(ride, allocation, _sla(), now=BASE_TIME + timedelta(minutes=6))
    assert decision == SupervisorDecision.START_NEXT_ATTEMPT


def test_waiting_past_deadline_marks_no_takers():
    ride = _ride(slot_start=BASE_TIME + timedelta(minutes=35))
    allocation = _allocation(
        AllocationStatus.WAITING_COOLDOWN.value,
        attempt_no=3,
        next_allowed=BASE_TIME + timedelta(minutes=3),
    )
    decision = decide_next_action(ride, allocation, _sla(), now=BASE_TIME + timedelta(minutes=10))
    assert decision == SupervisorDecision.MARK_NO_TAKERS
