"""Interactive simulation runner for stepping through supervisor ticks."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Dict

from transport_demo import db, ride_repository, sla_repository
from .api_dummy import generate_dummy_rides
from .config import SIM_ACCEPTANCE_RATE
from .simulation import simulate_tick, summarize_statuses


def seed_environment(conn, ride_count: int) -> None:
    db.init_db(conn)
    sla_repository.seed_default_sla(conn)
    if ride_count > 0:
        generate_dummy_rides(conn, count=ride_count)
    conn.commit()


def run_step(conn, acceptance_rate: float, now: datetime | None = None) -> Dict:
    now = now or datetime.now(timezone.utc)
    simulate_tick(conn, now=now, acceptance_rate=acceptance_rate)
    conn.commit()
    return {
        "summary": summarize_statuses(conn),
        "live_offers": ride_repository.list_live_offers(conn),
        "dead_letters": ride_repository.list_dead_letters(conn),
    }


def interactive_loop(steps: int, acceptance_rate: float, seed_rides: int, auto: bool) -> None:
    with db.db_session() as conn:
        seed_environment(conn, seed_rides)
        current_step = 0
        while steps <= 0 or current_step < steps:
            result = run_step(conn, acceptance_rate)
            current_step += 1
            print(f"\n=== Step {current_step} ===")
            print("Summary:", result["summary"])
            if result["live_offers"]:
                print("Live offers:")
                for offer in result["live_offers"]:
                    print(
                        f"  Ride {offer['ride_id']} attempt {offer['attempt_no']} -> {offer['status']} | "
                        f"{offer['pickup_address']} -> {offer['drop_address']}"
                    )
            else:
                print("No live offers")
            if result["dead_letters"]:
                print("Dead letters:", len(result["dead_letters"]))
            if not auto:
                user_input = input("Press Enter for next step (or 'q' to quit): ").strip().lower()
                if user_input == "q":
                    break


def main() -> None:
    parser = argparse.ArgumentParser(description="Run interactive supervisor simulation.")
    parser.add_argument("--steps", type=int, default=5, help="Number of steps to run (0 for infinite).")
    parser.add_argument(
        "--acceptance-rate",
        type=float,
        default=SIM_ACCEPTANCE_RATE,
        help="Probability that an offer is auto-accepted per attempt.",
    )
    parser.add_argument("--seed-rides", type=int, default=1, help="How many dummy rides to seed initially.")
    parser.add_argument("--auto", action="store_true", help="Run without waiting for user input between steps.")
    args = parser.parse_args()
    interactive_loop(args.steps, args.acceptance_rate, args.seed_rides, args.auto)


if __name__ == "__main__":  # pragma: no cover
    main()
