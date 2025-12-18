# Local Setup & Deployment Guide

Follow these steps to run the transport allocation prototype on a development machine.

## 1. Python environment
1. Install Python 3.11+.
2. Create and activate a virtual environment (recommended).
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *Leave `psutil` commented unless you plan to run `monitor_scenarios.py` for CPU/RAM sampling.*

## 2. Initialize the database
The prototype ships with SQLite and creates `transport_demo.db` in-place. No manual action is needed, but you can remove the file to reset state.

## 3. Run automated tests
```bash
pytest
```

## 4. Start core services
In separate terminals:
```bash
python -m transport_demo.main_supervisor
python -m transport_demo.main_offer_worker
```
Both scripts will seed the SLA table and keep looping according to `config.SUPERVISOR_POLL_INTERVAL_SEC`.

## 5. Launch APIs (optional)
Driver/ride API:
```bash
uvicorn transport_demo.api_dummy:app --reload --port 8000
```
Dashboard/admin API:
```bash
uvicorn transport_demo.dashboard_api:app --reload --port 8001
```

## 6. Generate rides for manual testing
Use the order generator (choose scenarios described in `SCENARIOS.md`):
```bash
python -m transport_demo.order_generator delhi_steady hyderabad_intermittent --runtime 120 --tick 5
```
This will create rides in real time; the supervisor/worker pair processes them automatically.

## 7. Optional monitoring
When you need CPU/RAM samples, install `psutil` and run:
```bash
python -m transport_demo.monitor_scenarios delhi_burst --steps 60 --acceptance 0.2 --tick 0.5
```
Remember to remove/comment this tooling before production.

## 8. Cleanup / reset
Delete `transport_demo/transport_demo.db` and restart the services to get a clean slate.

Refer to `PROJECT_FLOW.md` for a walkthrough of the runtime flow and `SCENARIOS.md` for the scenario catalog handed to the intern.
