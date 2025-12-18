from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

class RideCreate(BaseModel):
    city_code: str
    area_code: str
    slot_start: datetime
    slot_end: datetime

    priority_tier: str = Field(default="STANDARD")

    pickup_lat: Optional[float] = None
    pickup_lng: Optional[float] = None
    drop_lat: Optional[float] = None
    drop_lng: Optional[float] = None

    pickup_address: Optional[str] = None
    drop_address: Optional[str] = None

    load_type: Optional[str] = Field(default="Mixed")
    load_weight_kg: Optional[float] = Field(gt=0)

    offered_rate: Optional[float] = Field(gt=0)

    retailer_id: Optional[int] = None
    retailer_name: Optional[str] = None
    retailer_phone: Optional[str] = None

    # --- VALIDATORS ---

    @validator("slot_start", "slot_end", pre=True)
    def ensure_datetime(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v

    @validator("slot_end")
    def validate_slot_window(cls, v, values):
        start = values.get("slot_start")
        if start and v <= start:
            raise ValueError("slot_end must be after slot_start")
        return v

    # --- COMPUTED PROPERTIES (NO VALIDATORS) ---

    @property
    def slot_start_ist(self) -> time:
        return self.slot_start.astimezone(IST).time()

    @property
    def slot_end_ist(self) -> time:
        return self.slot_end.astimezone(IST).time()


class OfferAccept(BaseModel):
    ride_id: int
    attempt_no: int
