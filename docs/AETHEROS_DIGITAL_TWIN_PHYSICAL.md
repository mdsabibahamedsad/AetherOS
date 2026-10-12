# AetherOS Physical Digital Twins

## Overview (§54-63)

Digital twins are state-backed simulacra for robots, rooms, lab instruments, and environments. They answer "what would happen if...?" WITHOUT touching the real environment. Reality is always authoritative.

## Twin Types

### RobotTwin
- Kinematic model (joints, pose)
- `predict(action)` → kinematic target
- Dynamics not modeled (stated in contract)

### RoomTwin
- Object placement, spatial relations
- `place(obj_id, x, y, mode="SIMULATED")`

### RepositoryTwin
- Files, deps, imports, tests, build/git state
- `impact_analysis` on overlay copy

### BrowserTwin
- Tabs, DOM/a11y, nav/form state
- Navigation, form fill simulation

### AutomationTwin
- Workflow dry-run
- Side effects: "none — dry run only"

### SwarmTwin
- Agent assignment, waves, handoffs, conflicts
- Cost/latency estimates from counts

### A2ATwin
- Peer reliability/latency from verified history
- Honest "I don't know" when no history

### MCPTwin
- Deterministic mocks for tools
- `SIMULATION_UNAVAILABLE` if no mock

## Sync & Drift (§31-32, §173-174)

```python
twin.sync(real_state, confidence)  # timestamped, latency measured
drift = twin.check_drift(real, tolerance)
# → {"drift": bool, "event": {...}, "action": "REALITY_GAP — replan"}
```

### Sim-to-Real Tracker
```python
tracker.add(predicted, actual)
tracker.error() → {"n", "mean_abs_error": {...}}
```

## Digital Twin Modes (§56)

| Mode | Description |
|-------|-------------|
| READ_ONLY | Observe only |
| SIMULATION | Predict outcomes |
| SHADOW | Mirror real, no control |
| MIRROR | 1:1 state sync |
| CONTROLLED_EXECUTION | Explicit opt-in for real actuation |

## Twin-First Execution (§30)

High-risk actions:
```
REAL WORLD
   ↑
verified simulation
   ↑
digital twin
   ↑
planned action
```

## Twin-First Execution

For high-risk actions:
1. Sync twin from real sensors
2. Simulate planned action in twin
3. Verify predicted outcome
4. Request approval if needed
5. Execute on real hardware
6. Observe real result
6. Check drift → update twin/model

## Reality Gap (§173)

```python
gap = twin.check_drift(real, tolerance=0.05)
if gap["drift"]:
    # emit REALITY_GAP event
    # trigger replan from real state
```

## Sim-to-Real (§142, §174)

Before trusting simulator:
```python
tracker.add(predicted, actual)
error = tracker.error()
# Returns mean absolute error per dimension
```

### RealityGap
```python
RealityGap:
    simulation_assumptions
    real_environment
    parameter_mismatch
    uncertainty
    domain_gap
```

## Repository Twin (§57-58)

- Files, deps, imports, tests, build, git state
- `impact_analysis` on overlay copy
- `write_file`, `delete_file`, `impact_analysis` actions
- Real filesystem NEVER touched in SIMULATION mode

## Browser Twin (§59)

- Tabs, DOM-a11y snapshots
- Navigation, form fills
- `redirects_predicted: "unknown — verify live"`

## Automation Twin (§60/§114)

- Trigger/workflow dry-run
- Side effects: "none — dry run only"

## Swarm Twin (§61/§115)

```python
plan(tasks, agents, handoff_cost_ms=50, conflict_p=0.05)
→ {"waves", "expected_handoffs", "handoff_overhead_ms",
   "conflict_risk", "note": "estimate from counts"}
```

## A2A Twin (§62/§116)

```python
history = [{"ok": True, "latency_ms": 10}, ...]
peer.predict_peer() → {"reliability": 0.5, "mean_latency_ms": 30}
```

## MCP Twin (§63)

```python
mocks = {"echo": lambda args: args}
twin.apply_simulated({"tool": "echo", "parameters": {}})
# → {"simulated": True, "mock_result": {"echo": {...}}}
```

No mock → `SIMULATION_UNAVAILABLE` (§63). Mock ≠ real.

## Drift Detection (§32, §206)

```python
twin.check_drift(real, tolerance=0.05)
→ {"drift": bool, "event": {...}, "action": "REALITY_GAP — replan"}
```

Drift events stored with timestamp for analysis.

## Sim-to-Real Validation (§115, §142)

```python
tracker.record(predicted, actual)
error = tracker.error()
# Returns mean absolute error per dimension
```

## Twin-First Execution (§30)

For high-risk actions:
1. Sync twin from real sensors
2. Simulate planned action in twin
3. Verify predicted outcome
4. Request approval if needed
5. Execute on real hardware
6. Observe real result
7. Check drift → update twin/model

## Master 52 Integration

Digital twins extend Master-52 twins with:
- Robot/room/lab instrument twins
- Timestamped sync with latency measurement
- Drift events with REALITY_GAP actions
- Sim-to-real error tracking
- Honest contract: dynamics NOT modeled

## Integration with Trust Fabric

- Twin predictions are SIMULATION mode
- Real execution requires Trust Fabric authorization
- Drift events feed RealityCheckEngine
- Sim-to-real error feeds model updates