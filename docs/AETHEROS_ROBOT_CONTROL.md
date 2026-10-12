# AetherOS Robot Control

## Control Hierarchy (§41)

```
Strategic AI (LLM: goals, decomposition, semantics)
    ↓
Task Planner (DAG: observe → ... → verify)
    ↓
Motion/Manipulation/Nav Planner (trajectories, grasps, routes)
    ↓
Controller (deterministic — never LLM per-loop)
    ↓
Actuator
```

**LLMs do high-level planning only.** Millisecond control loops are deterministic code.

## Motion Stack

### Planners
- **A*** over FREE cells (unknown/occupied = blocked)
- Trapezoidal time-parameterization (vmax/amax/jmax)
- Grasp selection from gripper opening + force/friction estimates
- Navigation respects zones, battery, comms

### Verification (§37-38)
```
command sent ≠ succeeded
Expectation declared pre-action
Verdicts: VERIFIED | PARTIAL_SUCCESS | ACTION_FAILED | VERIFICATION_FAILED | UNKNOWN
Ack without independent evidence = UNKNOWN, never SUCCESS (§204)
```

## Safety Architecture (§42-43)

### Independent Safety Layer
```
AI
↓
High-Level Planner
↓
Trust Fabric (policy)
↓
Robot Controller
↓
Independent Safety Layer (authoritative)
↓
Actuator
```

**LLM cannot override:**
- Emergency stop
- Hardware safety limits
- Collision boundaries
- Restricted zones
- Human-safety policy

### Zones & People (§25-26)
- **KEEP_OUT** - hard veto
- **SLOW_ZONE / COLLABORATIVE** - speed caps
- **SAFE_ZONE** - normal operation
- **EMERGENCY_ZONE** - immediate stop

Human-nearby + MEDIUM/HIGH risk → denied or slowed.

### Emergency Stop (§44)
`aetheros physical stop` (and `SafetyController.emergency_stop`)
- Blocks new actions
- Requests hardware stop via adapters
- Cancels pending motion
- Preserves telemetry
- Records hash-chained incident
- Fans out to Master-50 global stop

Clearing requires explicit actor; resumption never blind (§103-104).

## Verification (§37-38)

`command sent ≠ succeeded`
Expectation declared pre-action.
Verdicts: VERIFIED | PARTIAL_SUCCESS | ACTION_FAILED | VERIFICATION_FAILED | UNKNOWN
Ack without independent evidence = UNKNOWN, never SUCCESS (§204).
Recovery selects from retry/relocalize/regrasp/retrajectory/retool/safe/human/abort — never blind retry (§58).

## Motion Stack

```
Strategic AI (LLM: goals, decomposition, semantics)
    ↓
Task Planner (DAG: observe..verify)
    ↓
Motion/Manipulation/Nav Planner (trajectories, grasps, routes)
    ↓
Controller (deterministic — §40, never LLM per-loop)
    ↓
Actuator
```

LLMs do high-level planning only. Millisecond control loops are deterministic code; edge-first (§223); cloud disconnect must never cause uncontrolled motion (§225); offline mode keeps local perception/planning/e-stop (§224).

## Verification Architecture

### Expectation Engine (§43)
```python
engine.expect(action_id, expected_state)
# ... execution ...
engine.compare(action_id, observed_state)
# Returns: VERIFIED | PARTIAL_SUCCESS | ACTION_FAILED | VERIFICATION_FAILED
```

### ActionVerifier (§37-38)
- Multi-source: ack + sensor + state + camera
- Ack alone = UNKNOWN, never SUCCESS (§204)
- State comparison with tolerance
- Expected vs observed comparison

## Robot Types

| Type | Capabilities | Safety |
|------|-------------|--------|
| Arm | MOVE, ROTATE, GRIP, RELEASE, PUSH | Force limits, collision |
| Mobile | MOVE, NAVIGATE, DOCK | Speed limits, zones |
| Humanoid | Full body | Full safety layer |
| Drone | TAKEOFF, LAND, HOVER, MOVE | Geofencing, altitude |
| Lab | DISPENSE, MIX, HEAT, MEASURE | Containment, ventilation |

## Verification Metrics

| Metric | Target |
|--------|--------|
| Grasp success | > 95% |
| Placement accuracy | < 2mm |
| Navigation success | > 99% |
| Collision rate | 0 |
| Recovery rate | > 90% |

## Emergency Stop Latency

| Layer | Target |
|-------|--------|
| Software trigger | < 1ms |
| Hardware signal | < 10ms |
| Mechanical stop | < 100ms |
| State preservation | < 10ms |

## Testing

```bash
# Safety tests
pytest tests/robot/safety -v

# Collision avoidance
pytest tests/robot/collision -v

# Emergency stop
pytest tests/robot/emergency_stop -v

# Verification accuracy
pytest tests/robot/verification -v
```

## Integration with Trust Fabric

- Robot commands pass through ActionFirewall
- Capability tokens required per action
- Safety layer is independent of Trust Fabric (authoritative)
- Human takeover → agent enters OBSERVE_ONLY
- Return to AI control requires explicit handoff