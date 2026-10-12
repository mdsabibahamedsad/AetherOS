# AetherOS Embodied Intelligence 1.0 (Master 54)

Intelligence layer for perceiving, reasoning about, simulating,
controlling, and safely interacting with the physical world.

**Core invariant: a model of the world is not the world.** Every
physical-world event carries an execution mode — `HARDWARE_UNAVAILABLE`
| `SIMULATION` | `REPLAY` | `LIVE_HARDWARE`. A prediction is not an
observation; a command is not an action; an action is not success;
only verified evidence closes the loop.

## Loop

```
PERCEIVE -> UNDERSTAND -> WORLD STATE -> SIMULATE -> PLAN
  -> AUTHORIZE -> ACT -> OBSERVE -> VERIFY -> LEARN
  -> UPDATE TWIN -> NEXT ACTION
```

## Package layout (`aetheros_embodied/`)

| Module | Covers |
|---|---|
| `models.py` | EmbodiedTask, PhysicalWorldState (StateVar: value/ts/source/confidence/freshness/mode), devices, robots, actions, telemetry, incidents |
| `frames.py` | Explicit frame tree + quaternion SE(3); no silent mixing |
| `registries.py` | Device/robot/actuator/capability registries; pairing; CredentialBroker (secrets never reach LLM) |
| `sensors.py` | Adapters, calibration, inverse-variance fusion, quality detection |
| `spatial.py` | Zones, occupancy maps (unknown != free), mapping, dead-reckoning localization, collision checking |
| `planning.py` | A* routing, time-parameterized trajectories (v/a/j limits), grasp heuristics, task DAGs |
| `twins.py` | Robot/room twins, timestamped sync, drift events, sim-to-real tracking |
| `simulation.py` | Kinematic simulator + contract (ideal kinematics; no dynamics/slip/contact) |
| `safety.py` | Independent veto layer, e-stop wired to Master-50, tamper-evident log |
| `execution.py` | Adapter interfaces, simulated robot, HMAC command auth + replay cache, rate limits, loop detection, closed-loop executor |
| `verification.py` | Expect-before-act; ack-only = UNKNOWN, never SUCCESS |
| `telemetry.py` | Event bus, clock model, ordering reports, privacy scrub, health |
| `security.py` | UI/QR/voice as data, remote default-deny, incidents |
| `memory.py` | TTL memory, environment-scoped skills, experience decay |
| `lab.py` | Instruments, validated protocols, Bayesian optimization (RBF+EI, toy scale), Pareto frontiers |
| `benchmarks.py` | SIMULATION/REPLAY benches; LIVE reports NOT_TESTED |
| `engine.py` | Facade: loop, autonomy L0-L5, budgets, checkpoints, recovery, approvals |
| `demo.py` | §260 pick-and-place + §261 science demos (SIMULATION) |

## Mode matrix

- No hardware: everything executes against kinematic sims / replay,
  labeled SIMULATION/REPLAY. `LIVE_HARDWARE` requires a registered
  third-party adapter + explicit authorization — none ships in core.
- First live action policy: minimal-risk, bounded, reversible,
  observable, verifiable, human-supervised (§259).

## Related docs

- `AETHEROS_PHYSICAL_WORLD_ARCHITECTURE.md` — state, frames, spatial
- `AETHEROS_HARDWARE_ADAPTERS.md` — adapter contracts + pairing
- `AETHEROS_ROBOT_CONTROL.md` — control hierarchy, real-time rules
- `AETHEROS_SENSOR_FUSION.md` — fusion math + quality
- `AETHEROS_PHYSICAL_SAFETY.md` — safetyumes, zones, e-stop
- `AETHEROS_DIGITAL_TWIN_PHYSICAL.md` — twin sync/drift/sim2real
- `AETHEROS_PHYSICAL_SECURITY.md` — threat model (§255) + defenses
- `AETHEROS_EMBODIED_BENCHMARKS.md` — bench design + results
- `AETHEROS_HARDWARE_INTEGRATION.md` — validation modes, first-hardware rules
