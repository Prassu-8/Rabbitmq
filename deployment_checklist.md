# Deployment Cleanup Checklist

Use this list to track prototype-only hooks and items that must change or be removed before production rollout.

1. **SQLite storage**
   - Replace `config.DB_PATH` with managed Postgres/MySQL and migrate schema.
   - Remove in-memory DB usage from tests/CLI.

2. **RabbitMQ stub usage**
   - Ensure `pika` connection details use production credentials.
   - Replace `simulation` RabbitMQ stubs with actual queues.

3. **Auto-acceptance logic**
   - Remove `SIM_ACCEPTANCE_RATE` random acceptance in `offer_worker.py`.
   - Driver acceptance must only come through real driver apps or `/offers/accept`.

4. **Dummy ride generation / monitoring tooling**
   - Disable `generate_dummy_rides` and CLI seeders (`sim_runner`, `load_test`, `order_generator`, `monitor_scenarios`) in prod.
   - Remove psutil-based monitoring code once real observability is in place.
   - Replace with real order ingestion sources.

5. **FastAPI test overrides**
   - Remove dependency overrides used in `tests/` before packaging.

6. **Dead-letter handling**
   - Integrate with real DLX/monitoring pipeline; remove placeholder `dead_letter_messages` table if replaced by MQ DLX.

7. **Logging & secrets**
   - Review logging for PII.
   - Move credentials/env defaults out of repo; use secret management.

8. **API auth**
   - Add authentication/authorization for `/rides`, `/offers/*`, `/dashboard/*`.

Keep this file updated whenever new prototype-only code is added.
