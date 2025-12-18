"""Run scenarios while capturing CPU/memory metrics.

Prototype-only helper that reuses :mod:`order_generator` and
:mod:`simulation`. Remove/disable before production.
"""
from __future__ import annotations

import argparse
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

import psutil

from . import db, sla_repository
from .order_generator import DEFAULT_SCENARIOS, OrderGenerator
from .simulation import simulate_tick, summarize_statuses


def run_scenario_metrics(
    conn,
    scenario_names: Iterable[str],
    steps: int,
    acceptance_rate: float,
    tick_sleep: float,
) -> dict:
    configs = [DEFAULT_SCENARIOS[name] for name in scenario_names]
    for cfg in configs:
        sla_repository.ensure_sla(
            conn,
            city_code=cfg.city_code,
            area_code=cfg.area_code,
            slot_start=cfg.slot_start,
            slot_end=cfg.slot_end,
            priority_tier=cfg.priority_tier,
        )
    generator = OrderGenerator(conn, configs)
    process = psutil.Process()
    process.cpu_percent(interval=None)
    cpu_samples: List[float] = []
    mem_samples: List[int] = []
    for _ in range(steps):
        now = datetime.now(timezone.utc)
        generator.tick(now)
        simulate_tick(conn, now=now, acceptance_rate=acceptance_rate)
        cpu_samples.append(psutil.cpu_percent(interval=None))
        mem_samples.append(process.memory_info().rss)
        if tick_sleep > 0:
            time.sleep(tick_sleep)
    summary = summarize_statuses(conn)
    return {
        "summary": summary,
        "cpu_avg": statistics.mean(cpu_samples) if cpu_samples else 0.0,
        "cpu_max": max(cpu_samples) if cpu_samples else 0.0,
        "mem_avg": statistics.mean(mem_samples) if mem_samples else 0.0,
        "mem_max": max(mem_samples) if mem_samples else 0,
    }


def run_all(scenarios: List[List[str]], steps: int, acceptance: float, tick_sleep: float) -> List[dict]:
    results = []
    with db.db_session() as conn:
        db.init_db(conn)
        for names in scenarios:
            result = run_scenario_metrics(conn, names, steps, acceptance, tick_sleep)
            result["scenarios"] = names
            results.append(result)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor scenarios with CPU/mem stats")
    parser.add_argument("scenarios", nargs="*", default=["delhi_steady", "hyderabad_steady"], help="Scenario names (space separated)")
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--acceptance", type=float, default=0.3)
    parser.add_argument("--tick", type=float, default=1.0)
    args = parser.parse_args()
    results = run_all([args.scenarios], args.steps, args.acceptance, args.tick)
    for res in results:
        print(f"Scenarios: {res['scenarios']}")
        print("Summary:", res["summary"])
        print(f"CPU avg {res['cpu_avg']:.2f}% max {res['cpu_max']:.2f}%")
        print(f"Mem avg {res['mem_avg']/1e6:.2f}MB max {res['mem_max']/1e6:.2f}MB")


if __name__ == "__main__":  # pragma: no cover
    main()
