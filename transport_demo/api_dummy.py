"""Driver-facing HTTP API for ride creation, live offers, and manual acceptance.

Backed by :mod:`transport_demo.ride_repository` / :mod:`transport_demo.sla_repository`
and typically served via Uvicorn during manual demos.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from transport_demo import db, ride_repository, sla_repository
from .models import AllocationStatus


def _tomorrow_slot_iso(slot_time_str: str) -> str:
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    hour, minute = [int(part) for part in slot_time_str.split(":")]
    dt = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return dt.isoformat()


def generate_dummy_rides(
    conn: sqlite3.Connection,
    count: int = 1,
    city_code: str = "DELHI",
    area_code: str = "NORTH_DELHI",
    priority_tier: str = "STANDARD",
) -> List[int]:
    slot_start_iso = _tomorrow_slot_iso("04:00")
    slot_end_iso = _tomorrow_slot_iso("06:00")
    sla = sla_repository.get_sla_for(
        conn,
        city_code=city_code,
        area_code=area_code,
        slot_start_iso=slot_start_iso,
        priority_tier=priority_tier,
    )
    if not sla:
        raise ValueError("SLA not configured")

    ride_ids: List[int] = []
    for i in range(count):
        ride_id = ride_repository.create_ride(
            conn,
            city_code=city_code,
            area_code=area_code,
            slot_start=slot_start_iso,
            slot_end=slot_end_iso,
            priority_tier=priority_tier,
            pickup_address=f"Pickup Yard {i+1}",
            drop_address=f"Drop Hub {i+1}",
            load_type="Mixed",
            load_weight_kg=500.0,
            offered_rate=900.0,
        )
        ride_repository.create_initial_allocation_for_ride(
            conn,
            ride_id=ride_id,
            max_attempts=sla.max_attempts,
        )
        ride_ids.append(ride_id)
    return ride_ids


class RideCreate(BaseModel):
    city_code: str = Field(default="DELHI")
    area_code: str = Field(default="NORTH_DELHI")
    slot_start: str
    slot_end: str
    priority_tier: str = Field(default="STANDARD")
    pickup_lat: Optional[float] = None
    pickup_lng: Optional[float] = None
    drop_lat: Optional[float] = None
    drop_lng: Optional[float] = None
    pickup_address: Optional[str] = None
    drop_address: Optional[str] = None
    load_type: Optional[str] = None
    load_weight_kg: Optional[float] = None
    offered_rate: Optional[float] = None
    retailer_id: Optional[int] = None
    retailer_name: Optional[str] = None
    retailer_phone: Optional[str] = None


class OfferAccept(BaseModel):
    ride_id: int
    attempt_no: int


app = FastAPI(title="Transport Demo API")


@app.post("/rides")
def create_ride(payload: RideCreate) -> dict:
    with db.db_session() as conn:
        sla = sla_repository.get_sla_for(
            conn,
            payload.city_code,
            payload.area_code,
            payload.slot_start,
            payload.priority_tier,
        )
        if not sla:
            raise HTTPException(status_code=400, detail="No SLA configured for ride scope")
        ride_id = ride_repository.create_ride(
            conn,
            city_code=payload.city_code,
            area_code=payload.area_code,
            slot_start=payload.slot_start,
            slot_end=payload.slot_end,
            priority_tier=payload.priority_tier,
            pickup_lat=payload.pickup_lat,
            pickup_lng=payload.pickup_lng,
            drop_lat=payload.drop_lat,
            drop_lng=payload.drop_lng,
            pickup_address=payload.pickup_address,
            drop_address=payload.drop_address,
            load_type=payload.load_type,
            load_weight_kg=payload.load_weight_kg,
            offered_rate=payload.offered_rate,
            retailer_id=payload.retailer_id,
            retailer_name=payload.retailer_name,
            retailer_phone=payload.retailer_phone,
        )
        ride_repository.create_initial_allocation_for_ride(
            conn,
            ride_id=ride_id,
            max_attempts=sla.max_attempts,
        )
        conn.commit()
        return {"ride_id": ride_id}


@app.get("/offers/live")
def list_live_offers() -> List[dict]:
    with db.db_session() as conn:
        offers = ride_repository.list_live_offers(conn)
        conn.commit()
        return offers


@app.post("/offers/accept")
def accept_offer(payload: OfferAccept) -> dict:
    with db.db_session() as conn:
        allocation = ride_repository.get_allocation_by_ride_id(conn, payload.ride_id)
        if not allocation:
            raise HTTPException(status_code=404, detail="Ride not found")
        if allocation.attempt_no != payload.attempt_no:
            raise HTTPException(status_code=400, detail="Attempt mismatch")
        if allocation.status not in (
            AllocationStatus.PENDING.value,
            AllocationStatus.SENT.value,
        ):
            raise HTTPException(status_code=400, detail="Attempt not active")
        ride_repository.mark_allocation_accepted(conn, allocation.allocation_id)
        ride_repository.mark_ride_accepted(conn, payload.ride_id)
        conn.commit()
        return {"status": "accepted"}
