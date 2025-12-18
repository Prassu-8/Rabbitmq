"""Domain models and enums used by the transport allocation prototype."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class RideStatus(str, Enum):
    NEW = "NEW"
    ALLOCATING = "ALLOCATING"
    ACCEPTED = "ACCEPTED"
    NO_TAKERS = "NO_TAKERS"
    COMPLETED = "COMPLETED"


class AllocationStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    SENT = "SENT"
    WAITING_COOLDOWN = "WAITING_COOLDOWN"
    ACCEPTED = "ACCEPTED"
    NO_TAKERS = "NO_TAKERS"


class SupervisorDecision(str, Enum):
    START_FIRST_ATTEMPT = "START_FIRST_ATTEMPT"
    START_NEXT_ATTEMPT = "START_NEXT_ATTEMPT"
    WAITING_COOLDOWN = "WAITING_COOLDOWN"
    STILL_ACTIVE_WAIT = "STILL_ACTIVE_WAIT"
    MARK_NO_TAKERS = "MARK_NO_TAKERS"
    NO_ACTION = "NO_ACTION"


@dataclass(slots=True)
class SLAProfile:
    sla_id: int
    city_code: str
    area_code: str
    slot_start: str
    slot_end: str
    priority_tier: str
    attempt_window_sec: int
    max_attempts: int
    cooldown_between_attempts_sec: int
    assign_before_slot_min: int
    target_delivery_window_min: int
    is_active: int
    created_at: str


@dataclass(slots=True)
class Ride:
    ride_id: int
    city_code: str
    area_code: str
    slot_start: str
    slot_end: str
    priority_tier: str
    pickup_lat: Optional[float]
    pickup_lng: Optional[float]
    drop_lat: Optional[float]
    drop_lng: Optional[float]
    pickup_address: Optional[str]
    drop_address: Optional[str]
    load_type: Optional[str]
    load_weight_kg: Optional[float]
    offered_rate: Optional[float]
    retailer_id: Optional[int]
    retailer_name: Optional[str]
    retailer_phone: Optional[str]
    status: str
    created_at: str
    updated_at: str

    def slot_start_dt(self) -> datetime:
        return datetime.fromisoformat(self.slot_start)


@dataclass(slots=True)
class RideAllocation:
    allocation_id: int
    ride_id: int
    attempt_no: int
    max_attempts: int
    attempt_start_at: Optional[str]
    attempt_expires_at: Optional[str]
    next_attempt_not_before: Optional[str]
    status: str
    created_at: str
    updated_at: str

    def attempt_start_dt(self) -> Optional[datetime]:
        return datetime.fromisoformat(self.attempt_start_at) if self.attempt_start_at else None

    def attempt_expires_dt(self) -> Optional[datetime]:
        return datetime.fromisoformat(self.attempt_expires_at) if self.attempt_expires_at else None

    def next_attempt_not_before_dt(self) -> Optional[datetime]:
        return (
            datetime.fromisoformat(self.next_attempt_not_before)
            if self.next_attempt_not_before
            else None
        )
