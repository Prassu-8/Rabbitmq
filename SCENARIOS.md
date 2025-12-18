# Scenario Catalog

Reference list of built-in order generator scenarios.

| Scenario name            | City / Area             | Spawn style                                | Typical usage |
|-------------------------|-------------------------|--------------------------------------------|---------------|
| `delhi_steady`          | Delhi / North Delhi     | Single ride every ~8s, continuous flow     | Baseline steady traffic |
| `hyderabad_steady`      | Hyderabad / Himayatnagar| Single ride every ~8s (slot 04:30–06:30)   | Alternate city steady state |
| `delhi_burst`           | Delhi / North Delhi     | Batch of 4 rides every ~20s                 | Stress test burst handling |
| `hyderabad_intermittent`| Hyderabad / Himayatnagar| Batch of 2 rides every 10s while active; pauses for 20s | Intermittent/pause-resume traffic |
| `delhi_steady + hyderabad_intermittent` | Mixed | Combines both configs simultaneously        | Cross-city concurrency |
| 

### Acceptance-rate suggestions
- 0.2–0.4: simulates low acceptance, triggers cooldowns/DLX.
- 0.6–0.8: higher acceptance to observe successful flows.
- 0.0: use when forcing NO_TAKERS for DLX/manual intervention testing.

Update this document if you add new entries to `DEFAULT_SCENARIOS` in `order_generator.py`.
