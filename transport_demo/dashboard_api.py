"""Dashboard/admin API exposing monitoring endpoints.

Uses :mod:`transport_demo.ride_repository` for DB reads and is intended for
operations teams to watch live stats, dead letters, and requeue rides.
"""
from __future__ import annotations

from typing import Generator, List

from fastapi import Depends, FastAPI, HTTPException, Query

from . import db, ride_repository

app = FastAPI(title="Transport Dashboard API")


def get_db_conn() -> Generator:
    with db.db_session() as conn:
        yield conn


@app.get("/dashboard/summary")
def dashboard_summary(
    window_min: int = Query(5, ge=1, le=120), conn=Depends(get_db_conn)
):
    summary = ride_repository.get_recent_attempts_summary(conn, window_minutes=window_min)
    return summary


@app.get("/dashboard/pending_manual")
def pending_manual_rides(conn=Depends(get_db_conn)) -> List[dict]:
    rides = ride_repository.get_pending_manual_rides(conn)
    return rides


@app.get("/dashboard/dead_letters")
def dead_letters(conn=Depends(get_db_conn)) -> List[dict]:
    return ride_repository.list_dead_letters(conn)


@app.post("/dashboard/requeue/{ride_id}")
def requeue_ride(ride_id: int, conn=Depends(get_db_conn)) -> dict:
    if not ride_repository.reset_allocation_for_retry(conn, ride_id):
        raise HTTPException(status_code=404, detail="Ride/allocation not found")
    ride_repository.clear_dead_letters_for_ride(conn, ride_id)
    return {"status": "requeued", "ride_id": ride_id}
