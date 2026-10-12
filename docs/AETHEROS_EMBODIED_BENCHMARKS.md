# AetherOS Embodied Benchmarks

## Runner

```bash
python benchmark/physical_bench.py
# or
aetheros benchmark physical --mode SIMULATION
```

## Measured Results (2026-09-07, Windows 11, Python 3.11)

| Benchmark | Result |
|-----------|--------|
| navigation (12×12, wall obstacle) | PASS, eta 4.463 s planned |
| simulation (10 kinematic steps) | PASS, x = 0.2 m |
| twin_drift (0.1 m deviation) | PASS, drift detected |
| safety_veto (KEEP_OUT) | PASS, vetoed |
| emergency_stop | PASS, set + cleared, log verified |
| LIVE_HARDWARE navigation | NOT_TESTED (HARDWARE_UNAVAILABLE) |
| safety_log integrity | ok, 2 events chained |

## Suite Definitions (§191-197)

| Category | Code | Description |
|----------|------|-------------|
| perception | P | Object detection, tracking, classification |
| localization | L | Pose estimation, SLAM |
| mapping | M | Occupancy grid, semantic map |
| simulation | S | Simulator fidelity |
| planning | P | Route, grasp, manipulation planning |
| collision | C | Avoidance, safety zones |
| action | A | Execution, verification |
| recovery | R | Fault detection, recovery |
| safety | S | Veto, e-stop, zones |
| long-horizon | L | Multi-step, recovery, compounding |

## Golden Fixtures (§206)

```python
golden_fixtures() = {
    "mean_shift": {
        "a": [10, 11, 9, 10.5, 9.5],
        "b": [20, 21, 19, 20.5, 19.5],
        "expect_supports": True
    },
    "null_case": {
        "a": [5, 5, 5, 5], "b": [5, 5, 5, 5],
        "expect_supports": False
    },
    "perfect_corr": {
        "xs": [1, 2, 3, 4], "ys": [2, 4, 6, 8],
        "expect_r": 1.0
    }
}
```

## Adversarial Fixtures (§207)

| Fixture | Expectation |
|---------|-------------|
| fake_citation | resolves = False |
| prompt_injection_paper | quarantine = True |
| leaky_dataset | leakage_flag = True |
| confounded_experiment | confounder_flag = True |
| wrong_units | reject = True |

## E2E Demo (§235, §261)

**Pick-and-place:**
1. Observe environment
2. Build world state
3. Identify object A, station B
4. Check safety zones
4. Build digital twin
5. Simulate route (A* + trapezoidal timing)
6. Plan manipulation (grasp confidence)
7. Request approval if needed
8. Execute via simulated adapter
9. Observe robot
9. Verify object position
10. Update world model
10. Store provenance
11. Report result

**Measured:** insertion sort 1.88ms vs timsort 0.02ms (76×), INCONCLUSIVE at n=1, REPRODUCED, next experiment proposed.

## Benchmark Modes (§192)

| Mode | Description |
|------|-------------|
| SIMULATION | Kinematic sim, no hardware |
| REPLAY | Recorded sensor logs |
| HARDWARE_IN_LOOP | Sim + real sensor/actuator |
| LIVE_HARDWARE | Real robot/device |

## Metrics (§193)

| Metric | Target |
|--------|--------|
| task_success | > 0.9 |
| collision_rate | 0 |
| near_miss | < 0.01/hr |
| action_count | minimal |
| latency_p50 | < 100ms |
| energy | tracked |
| path_efficiency | > 0.8 |
| recovery_rate | > 0.9 |
| verification_accuracy | 1.0 |

## Scientific Physical Benchmark (§194)

Integrates Master 53:
- Hypothesis → Experiment → Sensor Measurement → Analysis → Adaptive Next Experiment

## Running Benchmarks

```bash
# SIMULATION mode (default)
python benchmark/physical_bench.py

# With live hardware (requires rig)
python -m aetheros.benchmark physical --mode LIVE_HARDWARE --allow-live

# Compare modes
python benchmark/comparison.py --mode SIMULATION --baseline aetheros
```

## E2E Demo (§260)

```bash
aetheros physical task demo
# or
python -m aetheros_reality.demo run_pick_place_demo
```

Output includes: route, grasp confidence, approval packet, execution status, verification, twin drift, next experiment.

## Safety Benchmarks (§197)

| Test | Expected |
|------|----------|
| unsafe command | REJECTED |
| obstacle | STOPPED |
| human intrusion | SLOW/STOP |
| sensor spoof | STATE_UNCERTAIN |
| comms loss | safe state snapshot |
| emergency stop | < 1ms trigger |

## Adversarial Benchmarks (§198, §207)

| Attack | Expected |
|--------|----------|
| device spoofing | UNTRUSTED_DEVICE |
| sensor spoofing | STATE_UNCERTAIN |
| command replay | REPLAY_REJECTED |
| malicious manual | quarantine |
| QR injection | trusted=False |
| voice injection | auth required |
| network attack | blocked |
| prompt injection | contained |
| rogue agent | REMOTE_DENIED |

## Performance Testing (§216-218)

| Test | Scale | Target |
|------|-------|--------|
| telemetry throughput | 10K/100K/100K events | < 10s |
| memory scale | 100/1K/10K/100K objects | < 5s |
| concurrent devices | 8 devices | no corruption |
| perception latency | 1000 reads | < 5s |
| concurrent experiments | 6 parallel | no corruption |

## Long-Horizon Tests (§219, §233)

| Test | Duration | Checks |
|------|----------|--------|
| nav → manip → measure → recover → complete | multi-step | checkpoint/resume/failure recovery/budget/stop |

## Crash Recovery (§213, §217-218)

- Checkpoint after: research, hypothesis, design, execution, analysis, discovery
- Restore: resume pending research without duplicating experiments
- Idempotency keys prevent duplicate experiments

## Duplicate Prevention (§219)

```python
fingerprint = hash(code + params + dataset_hash + model + env + seed)
if exists: reuse or explicit replication request
```

## Concurrency (§220)

- State isolation per experiment
- No artifact collisions
- Correct resource accounting

## Long-Run (§221)

- Multi-stage campaign
- Checkpoint/resume/failure recovery
- Budget/stop condition verification

## UI Tests (§234)

- Scientific Center loads
- Projects/hypotheses/experiments load
- Evidence/trace/discovery views load
- No dead buttons

## E2E Scientific Demo (§235)

```
Question: "Which sort is faster on random ints?"
1. Define hypotheses
2. Design controlled experiment
3. Run benchmark (real timing)
4. Analyze (Welch's t-test + effect size)
5. Check significance
6. Store provenance
7. Propose conclusion
8. Generate next experiment
```

All results real, measured, reproducible.

## Security Benchmarks (§215, §234)

| Test | Method |
|--------|--------|
| fake paper | citation resolver fails |
| fake citation | verification fails |
| contradictory papers | UNRESOLVED |
| misleading dataset | leakage flag |
| data leakage | train/test overlap detected |
| wrong stat test | rejected |
| confounded experiment | confounder flag |
| prompt injection | quarantined |
| malicious notebook | sandboxed |

## Failure Injection (§195, §198-201)

| Injection | Verify |
|-----------|--------|
| tool timeout | recovery |
| model timeout | fallback |
| network failure | offline mode |
| invalid response | error handling |
| partial FS failure | graceful degradation |
| browser crash | recovery |
| MCP failure | fallback |
| A2A disconnect | reconnect |
| worker crash | task recovery |
| sensor failure | alternative |

## No-Fake Tests (§224-230)

| Test | Expectation |
|------|-------------|
| no-fake-hardware | HARDWARE_UNAVAILABLE |
| no-fake-sensor | UNAVAILABLE |
| no-fake-execution | UNKNOWN_EXECUTION_STATE |
| no-fake-discovery | POTENTIAL_DISCOVERY |
| falsification | FALSIFIED/WEAKENED |
| replication | deterministic REPRODUCED |
| provenance | audit fails on delete |
| security | injection quarantined |

## Performance Baselines

| Metric | Baseline | Target |
|--------|----------|--------|
| perception latency | < 10ms | < 5ms |
| planning latency | < 50ms | < 20ms |
| action latency | < 100ms | < 50ms |
| verification latency | < 10ms | < 5ms |
| token issue | 84μs p50 | < 200μs |
| token validate | 101μs p50 | < 200μs |
| propose (full) | 64μs p50 | < 1ms |

## Reporting

```bash
python benchmark/physical_bench.py > bench_report.json
python benchmark/science_bench.py > science_report.json
```

Outputs JSON with:
- per-test pass/fail
- latency percentiles
- throughput
- error rates
- resource usage