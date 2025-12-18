"""Load/performance scenario tooling for supervisor + worker simulation."""
from __future__ import annotations

import argparse
import statistics
import time
from datetime import datetime, timedelta, timezone
from typing import List

from . import db, ride_repository, sla_repository
from .api_dummy import generate_dummy_rides
from .simulation import simulate_tick, summarize_statuses


def _seed(conn, rides: int) -> None:
    db.init_db(conn)
    sla_repository.seed_default_sla(conn)
    if rides:
        generate_dummy_rides(conn, count=rides)
    conn.commit()


def run_scenario(
    conn,
    duration_sec: int,
    ride_rate_per_minute: int,
    acceptance_rate: float,
) -> dict:
    """Run simulation for duration, injecting new rides at given rate."""
    _seed(conn, rides=0)
    start = datetime.now(timezone.utc)
    end = start + timedelta(seconds=duration_sec)

    last_spawn_time = start
    spawn_interval = 60 / ride_rate_per_minute if ride_rate_per_minute > 0 else None
    tick_count = 0
    durations: List[float] = []

    while datetime.now(timezone.utc) < end:
        before = time.perf_counter()
        simulate_tick(conn, now=datetime.now(timezone.utc), acceptance_rate=acceptance_rate)
        conn.commit()
        tick_duration = time.perf_counter() - before
        durations.append(tick_duration)
        tick_count += 1

        if spawn_interval:
            now = datetime.now(timezone.utc)
            if (now - last_spawn_time).total_seconds() >= spawn_interval:
                generate_dummy_rides(conn, count=1)
                conn.commit()
                last_spawn_time = now

    summary = summarize_statuses(conn)
    return {
        "ticks": tick_count,
        "mean_tick_ms": statistics.mean(durations) * 1000 if durations else 0.0,
        "p95_tick_ms": statistics.quantiles(durations, n=20)[18] * 1000 if len(durations) >= 20 else 0.0,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Load scenario runner.")
    parser.add_argument("--duration-sec", type=int, default=30)
    parser.add_argument("--ride-rate", type=int, default=2, help="Rides spawned per minute.")
    parser.add_argument("--acceptance-rate", type=float, default=0.2)
    args = parser.parse_args()
    with db.db_session() as conn:
        result = run_scenario(conn, args.duration_sec, args.ride_rate, args.acceptance_rate)
        print("Total ticks:", result["ticks"])
        print(f"Mean tick: {result['mean_tick_ms']:.2f} ms")
        print(f"P95 tick: {result['p95_tick_ms']:.2f} ms")
        print("Summary:", result["summary"])


if __name__ == "__main__":  # pragma: no cover
    main()
