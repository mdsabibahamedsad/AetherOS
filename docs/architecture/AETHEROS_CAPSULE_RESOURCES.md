# AetherOS Capsule Resources

Implementation: `kernel/core/resource_manager.py`,
`kernel/core/hypervisor/hypervisor.py` (`_enforce_budgets`, quotas,
breakers, buckets, GC).

## Quotas (§25)

Per-capsule `ResourceBudget` slices: CPU, RAM, GPU/VRAM/NPU
(accounting-only — see below), disk, network, process count, threads
(policy), file descriptors (policy), browser/computer/device sessions,
model tokens, tool calls, agent children. Profiles are lean by default:
scarce sessions are requested only by the profiles that need them
(browser → 1 browser session, computer_use → 1 computer session,
physical/ambient → 1 device session, automation → 1 automation slot).

Admission charges the capsule slice, not the host-wide default: the
agent process is allocated the profile budget, and the admission-time
reservation is released after allocation (no reservation leak).

## Enforcement (§26) — real, not display-only

- CPU/RAM/disk/network/token expectations gate admission (insufficient →
  `PermissionError: insufficient resources`, naming the limit).
- Tool-call velocity, network quota, and child-agent quota are enforced
  in `invoke()` (deny with reason: stop/escalate, blocked, spawn denied).
- GPU: honest `NOT_SUPPORTED` — `gpu_status()` reports accounting-only;
  no time-slicing or memory enforcement is claimed (§27).

## Containment (§60–§66)

- Failure containment: capsule FAILED/QUARANTINE never propagates unless
  a dependency policy says so; kernel and sibling capsules unaffected.
- Circuit breakers per agent/capsule/tool/model/provider/node/device/
  network: CLOSED → OPEN (threshold) → HALF_OPEN (probe) → CLOSED.
- Rate limits per scope+action (fixed-window buckets, profile-tunable).
- Recursion: delegation depth (kernel max), per-capsule `max_children`,
  hypervisor capacity cap; automation capsules carry trigger/execution
  budgets; extensions run inside the capsule boundary, never around it.
- Swarms (§64, Master 42): parent capsule holds a collective quota
  (`set_swarm_quota`); `check_swarm_quota` aggregates worker usage and
  reports overruns — workers cannot jointly exceed it.

## Placement, battery, market (§103–§108)

`placement()` pins NO_NETWORK/local-only/physical capsules to `local`
with reasons; remote targets require pairing (REQUIRES_CONFIGURATION).
Battery/thermal/power hints ride in device policy for scheduling; node
advertising/pricing (Master 47) is modeled as data (`PlacementDecision`
reasons/warnings) with **no automatic spending** — purchases remain
explicitly authorized operations.

## GC and leaks (§117–§118)

`gc()` reclaims expired/terminal capsules past TTL (registry-persisted
for audit), trims bounded logs, expires secret values; `destroy()` never
deletes persistent artifacts implicitly. `leak_scan()` reports orphan
processes (agents without live capsules), orphan mounts (dirs without
records), reservations, and sessions.
