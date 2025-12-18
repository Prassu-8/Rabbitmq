"""Order generator worker that creates rides per scenario configuration.

Used by ``python -m transport_demo.order_generator`` as well as helper scripts
such as :mod:`transport_demo.monitor_scenarios` and :mod:`transport_demo.load_test`
to keep the supervisor/worker pipeline fed with synthetic rides.
"""
from __future__ import annotations

import argparse
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional

from . import db, ride_repository, sla_repository

LOGGER = logging.getLogger(__name__)


@dataclass
class ScenarioConfig:
    name: str
    city_code: str
    area_code: str
    priority_tier: str = "STANDARD"
    slot_start: str = "04:00"
    slot_end: str = "06:00"
    spawn_interval_sec: int = 10
    batch_size: int = 1
    active_duration_sec: int = 0  # 0 = always active
    pause_duration_sec: int = 0
    initial_delay_sec: int = 0


@dataclass
class ScenarioState:
    config: ScenarioConfig
    last_spawn: Optional[datetime] = None
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    next_phase_time: Optional[datetime] = None
    active: bool = True
    spawn_count: int = 0

    def __post_init__(self) -> None:
        self.start_time = datetime.now(timezone.utc) + timedelta(seconds=self.config.initial_delay_sec)
        if self.config.active_duration_sec > 0:
            self.next_phase_time = self.start_time + timedelta(seconds=self.config.active_duration_sec)
        elif self.config.pause_duration_sec > 0:
            self.next_phase_time = self.start_time + timedelta(seconds=self.config.pause_duration_sec)


DEFAULT_SCENARIOS: Dict[str, ScenarioConfig] = {
    "delhi_steady": ScenarioConfig(
        name="delhi_steady",
        city_code="DELHI",
        area_code="NORTH_DELHI",
        spawn_interval_sec=8,
        batch_size=1,
    ),
    "hyderabad_steady": ScenarioConfig(
        name="hyderabad_steady",
        city_code="HYDERABAD",
        area_code="HIMAYATNAGAR",
        slot_start="04:30",
        slot_end="06:30",
        spawn_interval_sec=8,
        batch_size=1,
    ),
    "delhi_burst": ScenarioConfig(
        name="delhi_burst",
        city_code="DELHI",
        area_code="NORTH_DELHI",
        spawn_interval_sec=20,
        batch_size=4,
    ),
    "hyderabad_intermittent": ScenarioConfig(
        name="hyderabad_intermittent",
        city_code="HYDERABAD",
        area_code="HIMAYATNAGAR",
        slot_start="05:00",
        slot_end="07:00",
        spawn_interval_sec=10,
        batch_size=2,
        active_duration_sec=30,
        pause_duration_sec=20,
    ),

}


def _parse_time(slot_str: str) -> Dict[str, int]:
    hour, minute = [int(part) for part in slot_str.split(":")]
    return {"hour": hour, "minute": minute}


def _slot_iso(slot_time: str) -> str:
    base = datetime.now(timezone.utc) + timedelta(days=1)
    parts = _parse_time(slot_time)
    dt = base.replace(second=0, microsecond=0, **parts)
    return dt.isoformat()


def _create_ride(conn, config: ScenarioConfig, state: ScenarioState) -> int:
    slot_start = _slot_iso(config.slot_start)
    slot_end = _slot_iso(config.slot_end)
    idx = state.spawn_count + 1
    pickup_address = f"{config.city_code} Pickup {idx}"
    drop_address = f"{config.city_code} Drop {idx}"
    ride_id = ride_repository.create_ride(
        conn,
        city_code=config.city_code,
        area_code=config.area_code,
        slot_start=slot_start,
        slot_end=slot_end,
        priority_tier=config.priority_tier,
        pickup_address=pickup_address,
        drop_address=drop_address,
        load_type=random.choice(["Vegetables", "Fruits", "Mixed"]),
        load_weight_kg=400 + random.randint(0, 200),
        offered_rate=800 + random.randint(0, 200),
        retailer_name=f"Retailer {idx}",
        retailer_phone=f"+91-98{random.randint(10000000, 99999999)}",
    )
    sla = sla_repository.get_sla_for(
        conn,
        config.city_code,
        config.area_code,
        slot_start,
        config.priority_tier,
    )
    if not sla:
        sla_repository.ensure_sla(
            conn,
            city_code=config.city_code,
            area_code=config.area_code,
            slot_start=config.slot_start,
            slot_end=config.slot_end,
            priority_tier=config.priority_tier,
        )
        sla = sla_repository.get_sla_for(
            conn,
            config.city_code,
            config.area_code,
            slot_start,
            config.priority_tier,
        )
    ride_repository.create_initial_allocation_for_ride(conn, ride_id, max_attempts=(sla.max_attempts if sla else 3))
    state.spawn_count += 1
    return ride_id


class OrderGenerator:
    def __init__(self, conn, scenarios: Iterable[ScenarioConfig]) -> None:
        self.conn = conn
        self.states = [ScenarioState(config=sc) for sc in scenarios]

    def tick(self, now: Optional[datetime] = None) -> int:
        now = now or datetime.now(timezone.utc)
        spawned = 0
        for state in self.states:
            spawned += self._maybe_spawn(state, now)
        if spawned:
            self.conn.commit()
        return spawned

    def _maybe_spawn(self, state: ScenarioState, now: datetime) -> int:
        cfg = state.config
        if now < state.start_time:
            return 0
        self._update_phase(state, now)
        if not state.active:
            return 0
        if state.last_spawn and (now - state.last_spawn).total_seconds() < cfg.spawn_interval_sec:
            return 0
        for _ in range(cfg.batch_size):
            ride_id = _create_ride(self.conn, cfg, state)
            LOGGER.info("Generated ride %s for scenario %s", ride_id, cfg.name)
        state.last_spawn = now
        return cfg.batch_size

    def _update_phase(self, state: ScenarioState, now: datetime) -> None:
        cfg = state.config
        if cfg.active_duration_sec <= 0 or cfg.pause_duration_sec <= 0:
            return
        if state.active and state.next_phase_time and now >= state.next_phase_time:
            state.active = False
            state.next_phase_time = now + timedelta(seconds=cfg.pause_duration_sec)
        elif not state.active and state.next_phase_time and now >= state.next_phase_time:
            state.active = True
            state.next_phase_time = now + timedelta(seconds=cfg.active_duration_sec)


def run_generator(scenario_names: List[str], runtime_sec: int, tick_interval: int) -> None:
    configs = [DEFAULT_SCENARIOS[name] for name in scenario_names]
    with db.db_session() as conn:
        db.init_db(conn)
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
        start = time.time()
        while runtime_sec <= 0 or (time.time() - start) < runtime_sec:
            spawned = generator.tick()
            LOGGER.info("Spawned %s rides this tick", spawned)
            time.sleep(tick_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Order generator worker")
    parser.add_argument("scenarios", nargs="*", default=["delhi_steady"], choices=list(DEFAULT_SCENARIOS.keys()))
    parser.add_argument("--runtime", type=int, default=60, help="How long to run in seconds (0=infinite)")
    parser.add_argument("--tick", type=int, default=5, help="Tick interval seconds")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    run_generator(args.scenarios, args.runtime, args.tick)


if __name__ == "__main__":  # pragma: no cover
    main()
