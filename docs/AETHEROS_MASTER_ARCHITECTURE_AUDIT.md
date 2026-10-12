# AetherOS Master Architecture Audit (Master 59, Phase A)

Method: traced real execution paths (imports executed, code paths read
end-to-end, tests run), not file listings. Baseline: `main` branch,
working tree dirty with ~1924 changed/untracked entries (prior-phase work
uncommitted, including all of `kernel/core/`); `import kernel.core` clean.

## 1. Current architecture (as built, not as drawn)

```text
USER
 ↓  natural language (CLI / gateway / desktop renderer → backend)
INTENT  (kernel/core/intent_manager.admit: validate → admission policies
         → resource check → risk → approval → authority grant + reservation)
 ↓
AGENT KERNEL  (kernel/core/kernel.py AgentKernel: 26 subsystems, DI via
              constructor args (config, event_bus, ...managers))
 ↓
CONTROL/GOVERNANCE  (policy_engine → security_boundary → audit_engine;
                     deterministic rules; quarantine + e-stop)
 ↓
SCHEDULER  (kernel/core/scheduler.py: heap by (priority, deadline,
           created, seq); admit/schedule/preempt/yield/block)
 ↓
POLICY/AUTHORITY  (authority_manager: create/grant/delegate with
                  ChildAuthority ⊆ ParentAuthority; revocation cascades)
 ↓
AGENT RUNTIME  (agent_process_manager: stub by default, live AIAgent only
               with AETHEROS_KERNEL_REAL_AGENT=1; run_agent.py AIAgent is
               the legacy conversational loop)
 ↓
CAPSULE/ISOLATION  (kernel/core/hypervisor/: capsule lifecycle, FS roots,
                    network policy, secret broker, receipts, snapshots)
 ↓
MODEL+MEMORY+TOOLS  (model_manager routing; memory_manager provider fan-out;
                     tool_manager → tools/registry.py → syscalls catalog)
 ↓
CAPABILITIES  (capability_invoker pipeline: descriptor → grant → policy →
              security → resources → provider → verification → audit)
 ↓
OBSERVE → VERIFY → MEMORY → AUDIT  (observability_engine, audit hash chain)
```

## 2. Actually implemented systems (verified)

- Intent admission with validation, risk, approval, grant, reservation
  (`intent_manager.py:64`, 292 lines, tested).
- Authority delegation with subset enforcement + cascading revocation
  (`authority_manager.py:165`, tested).
- Capability syscall pipeline with fail-closed denials
  (`capability_invoker.py:87`, tested).
- Scheduler with heap tiebreak, preemption, starvation boost
  (`scheduler.py`, tested; tiebreak fixed in Master 58 with evidence).
- Checkpoints (agent + capsule snapshots with integrity hashes) and
  recovery planning (`checkpoint_manager`, `recovery_manager`,
  hypervisor snapshots, tested incl. tamper rejection).
- Policy engine with deterministic rules + evaluation cache
  (`policy_engine.py`, tested).
- Security boundary: injection patterns, IFC, quarantine, e-stop
  (`security_boundary.py`, tested).
- Hash-chained audit log with persistence (`audit_engine.py`, tested).
- Tool registry bridge: 72 tools as `tool.*` + 27 syscall aliases
  (`tool_manager.py`, `syscalls.py`, tested).
- Network manager with allow/deny/IP rules, budgets
  (`network_manager.py`, tested).
- Sandbox backends with detection (`aetheros_security/sandbox`,
  `hub/sandbox.py`, tested per backend availability).
- Electron preload as curated allowlist (`preload.cjs`, 141 lines, no raw
  privileged exposure); `aetheros:api` proxies to same-host backend only.
- CLI via argparse subparsers (`main.py` 518KB), incl. `aetheros capsule`
  (Master 58, smoke-verified cross-process).

## 3. Partially implemented (real gaps found by tracing)

1. `capability_invoker._check_resource_availability` returns `True`
   unconditionally (`capability_invoker.py:264`) — per-call resource gate
   is a no-op; enforcement lives at admission + hypervisor budgets only.
2. `_verify_attest` returns `verified: True` with note "not fully
   implemented" (`capability_invoker.py:321`) — a fake verification.
3. `_check_information_flow` network-egress branch is a `pass`
   (`capability_invoker.py:287`) — kernel-level IFC for network targets
   relies on hypervisor + network_manager.
4. `ModelProfile.availability` (float) is never used as a filter;
   `select_model` filters only `health == "healthy"`. An unconfigured
   provider's models remain selectable.
5. `checkpoint_manager.create_checkpoint(agent_id)` builds a *minimal*
   checkpoint (empty process/intent fields); only `create_full_checkpoint`
   and capsule snapshots capture real state.
6. `AgentProcessManager` defaults to a stub runtime; live path requires
   env opt-in and is untested here.
7. `aetheros:api` IPC bridge has no renderer-side path allowlist; safety
   depends on same-host baseUrl + backend token auth (verified present).
8. Remote capsule migration, VM/container backends, GPU enforcement:
   explicitly unimplemented (honestly reported, Master 58).

## 4. Duplicated systems (confirmed by class inventory)

| Concept | Implementations | Canonical (used by kernel path) |
|---|---|---|
| EventBus | kernel/event_bus, aetheros_orchestrator/bus, aetheros_automation/orchestrator/events, aetheros_embodied/telemetry, aetheros_integrations/events, aetheros_memory_intelligence/events, extensions/events (+ agent_market) | kernel/event_bus |
| CapabilityRegistry | kernel CapabilityManager, aetheros_control_plane/identity_plane, aetheros_embodied/registries, extensions/registry, swarm/capabilities, aetheros_agent_economy/capabilities | kernel CapabilityManager |
| PolicyEngine | kernel/core, extensions/policy, enterprise/policy_engine, agent/multimodal/ci_cd | kernel/core |
| PermissionEngine | aetheros_security/permissions, aetheros_extensions/permissions | aetheros_security/permissions (CLI surface) |
| MemoryManager | kernel/core, agent/memory_os/manager, agent/memory_manager, memory/memory_manager, aetheros_memory/memory_manager (+ memory_manager_original.py, temp_test.py copies) | kernel/core (provider fan-out; memory_os not wired to it) |
| TaskGraph | kernel/task_graph, aetheros_automation/tasks/graph, core/jarvis/planner, agent/orchestration/types | none canonical for kernel path (TaskManager is) |
| Planner | kernel/planner, aetheros_cognitive/planner, + PlannerAgents | kernel/planner (legacy; core path uses intent→scheduler) |
| ModelRouter | kernel ModelManager, aetheros_automation/routing, aetheros_automation/orchestrator/routing, aetheros_intelligence/model_router | kernel ModelManager |
| Checkpoint stores | kernel CheckpointManager, tools/checkpoint_manager (FS), aetheros_computer/task_checkpoint, aetheros_reliability/checkpoint, capsule snapshots | kernel + capsule snapshots (linked by refs, §7) |
| Sandbox | aetheros_security/sandbox, hub/sandbox.py | aetheros_security/sandbox (CLI); hypervisor providers detect |

`apps/desktop/dist-packaged/` is a build artifact copy (excluded from
counts). `memory_manager_original.py` / `temp_test.py` are dead copies.

## 5. Broken systems (with evidence)

- Scheduler heap `TypeError` on tied keys — FIXED in Master 58 (seq +
  `__lt__`, regression-tested).
- Admission reservation leak (one reservation per agent, never released)
  — FIXED in Master 58 (released post-allocation in
  `create_agent_process`).
- `aetheros:api` has no path allowlist (moderate; backend token auth
  verified, host pinned to baseUrl) — documented, hardening added §7.

## 6. Missing systems (vs Master 59 target)

- Canonical typed error taxonomy (§35): errors are builtin
  PermissionError/ValueError/KeyError/RuntimeError — implemented §7.
- Versioned Intent envelope (§5): Intent has no version/signature fields
  — implemented §7 (additive).
- Canonical task lifecycle uniting TaskManager states with TaskGraph DAGs
  (§6): mapped + adapter in §7 (no rewrite).
- Concurrency tests for scheduler/capsule paths (§40): added §8.
- Cross-artifact benchmark harness (§59): added §8 (real measurements).
- Capsule Center desktop UI (Master 58 deferred): still deferred; data
  API complete.
- Mobile clients: `apps/ios` exists; capability gating per §54
  unverified here — documented as BLOCKED (no simulators on Windows).

## 7. Integration gaps

- `agent/memory_os` (rich manager) is NOT wired to kernel MemoryManager
  providers — consolidation via provider adapter, §7.
- Legacy planners/routers/graphs orbit the kernel path but don't drive
  it — mapped to canonical equivalents, adapters where cheap, §7.
- Filesystem checkpoints (`tools/checkpoint_manager`) and agent/capsule
  snapshots reference each other only by convention — linked explicitly
  in capsule `filesystem_meta`, §7.
- Cron/automation (`cron/`, `aetheros_automation/`) enter via intents in
  the kernel path but keep separate stores — documented, not rewritten.

## 8. Dependency graph (actual)

```text
kernel.core.types  (no deps — imported by all core modules)
       ↑
kernel/event_bus, kernel/lifecycle  (infra, no core deps)
       ↑
core managers  (each: config + event_bus + explicit manager refs;
               authority→policy+security; invoker→all; hypervisor→kernel)
       ↑
AgentKernel  (constructs all; hypervisor last; shuts down hypervisor first)
       ↑
KernelSDK / CapsuleAPI / syscalls catalog / CLI  (facades only)
```

Prohibited and verified absent: model→policy bypass (models never
authorize), tool→direct host (all via invoker/providers), renderer→raw
privileged APIs (preload allowlist), remote→local privileged invoke
(manifest/grant gates, tested). No circular imports: `import kernel.core`
clean.

## 9. Critical risks

1. Tree has ~1924 dirty entries (prior-phase work uncommitted) — review
   and commit discipline risk, not code risk.
2. Five memory systems + seven event buses invite future bypasses;
   canonical-path tests pin the safe route (§8 invariants).
3. Attestation fake-verification and no-op resource gate (fixed §7).
4. Unconfigured models selectable (fixed §7: availability filter).
5. Generic IPC bridge relies on backend auth (hardened §7 with path
   allowlist).

## 10. Consolidation order (executed)

P1: error taxonomy → intent envelope → verification honesty fixes →
model availability → task-model adapter → memory_os provider bridge →
checkpoint linkage → IPC hardening → concurrency tests → benchmarks →
docs → certification matrix → completion report.
