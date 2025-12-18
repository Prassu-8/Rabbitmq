from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Literal

# -------------------------------------------------
# Common / Reusable Schemas
# -------------------------------------------------

class Location(BaseModel):
    lat: float
    lng: float
    city_code: Optional[str] = None
    area_code: Optional[str] = None
    address: str


class LoadDetails(BaseModel):
    type: str
    weight_kg: float


class RetailerInfo(BaseModel):
    id: int
    name: str
    phone: str


# -------------------------------------------------
# 1️⃣ Incoming Ride Request Event (Retailer → System)
# -------------------------------------------------

class RideCreatedEvent(BaseModel):
    job_id: int

    pickup_location: Location
    dropoff_location: Location

    slot_start: datetime
    slot_end: datetime

    priority_tier: Literal["high", "standard", "low"]

    load_details: LoadDetails
    offered_rate: float

    retailer_info: RetailerInfo

    status: Literal[
        "NEW",
        "ALLOCATING",
        "ACCEPTED",
        "NO_TAKERS",
        "COMPLETED",
    ]

    created_at: datetime
    updated_at: Optional[datetime] = None


# -------------------------------------------------
# 2️⃣ Outgoing Driver Offer Event (System → Drivers)
# -------------------------------------------------

class DriverOfferEvent(BaseModel):
    job_id: int

    pickup_location: Location
    dropoff_location: Location

    load_details: LoadDetails

    estimated_distance_km: float
    delivery_date: date

    offered_rate: float
    priority_tier: Literal["high", "standard", "low"]

    vehicle_id: int
    driver_id: Optional[int] = None

    status: Literal["NEW", "EXPIRED", "MATCHED"]


# -------------------------------------------------
# 3️⃣ Driver Acceptance Event (Driver → System)
# -------------------------------------------------

class DriverAcceptedEvent(BaseModel):
    job_id: int
    driver_id: int
    vehicle_id: int
    accepted_at: datetime
