# Project Flow Overview

This document explains the high-level runtime flow and references the files that implement each step.

1. **Configuration (`config.py`)**
   - Defines DB path, RabbitMQ settings, poll intervals, and optional simulation acceptance rate.

2. **Database & repositories (`db.py`, `sla_repository.py`, `ride_repository.py`)**
   - `db.py` provides SQLite helpers.
   - `sla_repository.py` manages SLA rows and is called from APIs/order generator/supervisor.
   - `ride_repository.py` exposes CRUD helpers used by every component (APIs, supervisor, worker, dashboards).

3. **Models & enums (`models.py`)**
   - Dataclasses for `SLAProfile`, `Ride`, `RideAllocation`, and enums for statuses/decisions.

4. **Supervisor loop (`supervisor.py`, `main_supervisor.py`)**
   - `main_supervisor.py` bootstraps the DB/SLA and starts the loop.
   - `supervisor.py` pulls pending allocations, decides next action, and publishes offers via `rabbitmq_client.py`.

5. **Offer worker (`offer_worker.py`, `main_offer_worker.py`)**
   - `main_offer_worker.py` initializes DB + RabbitMQ and subscribes to `offer.create`.
   - `offer_worker.py` validates attempt numbers and marks allocations as SENT/ACCEPTED.

6. **RabbitMQ client (`rabbitmq_client.py`)**
   - Thin wrapper used by supervisor and worker to publish/consume messages.

7. **APIs**
   - Driver ride API (`api_dummy.py`): create rides, list live offers, manual accept endpoint.
   - Dashboard API (`dashboard_api.py`): summary metrics, pending manual rides, dead-letter view, requeue endpoint.

8. **Order generation & simulators**
   - `order_generator.py`: produces rides per scenario for testing.
   - `sim_runner.py` + `simulation.py`: step-by-step simulator for controlled experiments.
   - `load_test.py`: synthetic load driver measuring DB-side effects.
   - `monitor_scenarios.py`: optional CPU/memory sampler (prototype-only).

9. **Entry points & scripts**
   - `main_supervisor.py`, `main_offer_worker.py`, `order_generator.py`, `load_test.py`, `monitor_scenarios.py` can all be run via `python -m transport_demo.<module>`.

10. **Tests (`transport_demo/tests/`)**
    - Cover repositories, supervisor logic, APIs, order generator, simulators, and monitoring helper.

For scenario-specific behavior, see `SCENARIOS.md`. For setup instructions, see `LOCAL_SETUP.md`.
