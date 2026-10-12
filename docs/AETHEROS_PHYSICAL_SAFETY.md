# AetherOS Physical Safety

## Independent Safety Layer (§42-43)

The SafetyController operates independently of the planner/LLM. It can stop, slow, limit, or reject actions. The LLM **cannot override**:

- Emergency stop
- Hardware safety limits
- Collision boundaries
- Restricted zones
- Human-safety policy

## Safety Architecture

```
AI / High-Level Planner
       ↓
Trust Fabric (policy + authorization)
       ↓
Independent Safety Layer (authoritative)
       ↓
Robot Controller / Actuator
```

Safety layer has veto power over all motion. LLM cannot bypass.

## Zones & Human Safety (§25-26, §213)

| Zone | Behavior |
|------|----------|
| KEEP_OUT | Hard veto - action denied |
| SLOW_ZONE | Speed capped at `speed_limit` |
| COLLABORATIVE_ZONE | Speed capped, force limits |
| SAFE_ZONE | Normal operation |
| EMERGENCY_ZONE | Immediate stop |

Human presence in COLLABORATIVE/SAFE zones with MEDIUM/HIGH risk actions → slow/stop per policy.

## Emergency Stop (§44, §208)

```python
emergency_stop(reason: str, actor: str) → StopState
```

**Effects:**
- Blocks new actions immediately
- Requests hardware stop via adapters
- Cancels pending motion
- Preserves telemetry
- Records hash-chained incident
- Fans out to Master-50 global stop

Clearing requires explicit actor; resumption never blind (§103-104).

## Safety Controller

```python
class SafetyController:
    def check_action(self, action: PhysicalAction, ctx: Dict) -> Dict[str, Any]:
        # Returns {allowed: bool, reasons: List[str]}
        # Vetoes are absolute
```

### Checks Performed
1. Emergency stop active → deny
2. KEEP_OUT zone → deny
3. Speed > zone limit → deny
3. Human nearby + MEDIUM/HIGH risk → deny
4. Force > limit → deny
5. Policy denial → deny

## Safety Log (§99)

Tamper-evident hash chain:
```python
def verify_log() -> {"ok": bool, "events": int}
```

Each event: `{kind, at, prev_hash, hash, payload}`

## Safety Classes

| Class | Risk | Action |
|-------|------|--------|
| COMPUTATIONAL | None | Auto-approve |
| LOW_RISK | Low | Auto-approve |
| REVIEW_REQUIRED | Medium | Human review |
| HIGH_RISK | High | Explicit approval |
| PROHIBITED | Extreme | Block |

## Human Takeover (§246-249)

```python
HumanTakeoverController:
    def take_over() → agent enters OBSERVE_ONLY
    def release() → explicit handoff required
```

AI never auto-resumes after human takeover (§249).

## Safety Classes for Devices

| Class | Examples | Requirements |
|-------|----------|--------------|
| COMPUTATIONAL | Pure software | Auto |
| LOW_RISK | Sensors, displays | Auto |
| REVIEW_REQUIRED | Actuators, tools | Human review |
| HIGH_RISK | Robots, welders, cutters | Explicit approval |
| PROHIBITED | Weapons, explosives | Block |

## Fail-Safe Behaviors

| Trigger | Response |
|---------|----------|
| Sensor failure | Safe state, alert |
| Network loss | Safe state (unless fail-safe says otherwise) |
| Power loss | Reinitialize, verify calibration, verify pose |
| Unexpected motion | Emergency stop |
| Human proximity (unexpected) | Slow/stop per policy |

## Testing

```bash
pytest tests/safety/ -v
```

Key tests:
- Emergency stop overrides everything
- Safety veto wins over planner
- Stale plans fail
- Sensor disagreement → uncertain
- Unknown device → no control
- Emergency stop overrides HIGH approved