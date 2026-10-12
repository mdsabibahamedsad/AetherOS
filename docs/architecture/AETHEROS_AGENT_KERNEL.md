# AetherOS Agent Kernel 1.0 — Architecture

The Agent Kernel is the trusted control plane for agent-native computing.
It sits between the host OS and the agent runtime, mediating every
capability invocation, scheduling decision, resource allocation, and
policy evaluation.

## Execution loop

```text
INTENT → ADMISSION → IDENTITY → AUTHORITY → PLAN → SCHEDULE
     → ALLOCATE → EXECUTE → OBSERVE → VERIFY → UPDATE
     → STORE MEMORY → AUDIT → LEARN → CONTINUE / COMPLETE / RECOVER
```

## Layers

```text
LAYER 0   Host OS (Windows / Linux / macOS)
LAYER 1   AetherOS Kernel Boundary
LAYER 2   Kernel Services
LAYER 3   Agent Runtime
LAYER 4   Capability Runtime
LAYER 5   Agent Applications / Skills / Automations
LAYER 6   User Experience
```

The Kernel never replaces the host OS; it is an agent-native abstraction
layer above it.

## Components

Implemented in `kernel/core/` — 25 subsystems plus `AgentKernel`:

| Subsystem | Role |
|---|---|
| AgentProcessManager | lifecycle + AIAgent bridge |
| IntentManager | admission, validation, risk, grant |
| AuthorityManager | grants, delegation, revocation |
| CapabilityManager | registration, discovery, metadata |
| CapabilityInvoker | syscall pipeline (authority → policy → security → resources → provider → verify → audit) |
| ResourceManager | budgets, allocation, release, quotas, backpressure |
| KernelScheduler | OS-like scheduler with priority, deadlines, quotas |
| ContextManager | allocation, compression, eviction, snapshots |
| MemoryManager | provider fan-out, scope isolation, provenance |
| ModelManager | routing, selection, cost, health, local-first |
| ToolManager | tool→capability bridge, sandbox |
| TaskManager | DAG execution, status, artifacts |
| CheckpointManager | create/restore, full + minimal, integrity |
| RecoveryManager | classify, plan, execute, verify side-effects |
| PolicyEngine | deterministic rules, cache, ALLOW/DENY/REQUIRE_APPROVAL |
| GovernanceEngine | compliance, violations, handlers |
| SecurityBoundary | injection, IFC, e-stop, quarantine |
| ProvenanceEngine | nodes/edges/lineage, tamper-evident |
| AuditEngine | hash-chained log, retention, query |
| ObservabilityEngine | traces, spans, metrics, sampling |
| CostManager | budgets, rates, per-task/agent |
| LatencyManager | p50/p95/p99, spans, histograms |
| ArtifactManager | versioned artifacts, quarantine |
| NetworkManager | allow/deny lists, IP rules, SSRF/DNS defense |
| DeviceManager | pairing, verification, telemetry |
| HumanOversightManager | approval requests, responses, remember |

## Integration

- Tools: `tool_manager.discover_tools()` → `tools/registry.py` (72 tools)
- Memory: providers fan out (kernel + Memory 2.0 via bridge)
- Models: `ModelManager` routes to providers, respects availability
- Capsules: `AgentHypervisor` creates/manages capsules (lifecycle, FS, net, secrets)
- Scheduler: wraps `KernelScheduler` + `cron/` for background work
- Tools: `syscalls.py` catalog (27 syscalls over tools + 5 native + 4 blocked)
- Capsules: `AgentHypervisor` manages isolation, secrets, checkpoints, migration
- Event bus: single `EventBus` for all subsystems + capsule events

## Security invariants (verified by `tests/kernel/test_agent_kernel_security.py`)

1. Child authority never exceeds parent authority
2. Untrusted content never becomes authority
3. Policy denial cannot be bypassed by model output
4. Renderer cannot grant backend authority
5. Remote agent cannot directly invoke privileged local capability
6. Revoked identity cannot execute
7. Expired approval cannot execute
8. Emergency stop cannot be overridden by agent
9. Secret data cannot cross forbidden boundary
10. Simulation cannot be reported as reality

## Verification honesty

- `CapabilityInvoker._verify_attest` returns UNVERIFIED (fail-closed) without provider attestation
- `_check_resource_availability` compares remaining budget vs required per dimension
- `_check_information_flow` blocks non-public data egress without granted network scopes
- Unconfigured providers (availability=0.0) excluded from model selection
- `ResourceBudget.zero()` used for true-zero allocations (no defaults leak)

## Resource accounting

`ResourceManager` tracks CPU, RAM, GPU, VRAM, disk, network, tokens, concurrency
slots, browser/computer/device sessions, research requests, agent/automation slots,
battery, thermal. Admission reserves; allocation allocates; release frees.

## Benchmarks (reference host: Windows, Python 3.11.15)

| op | n | p50 (ms) | p95 (ms) | p99 (ms) | mean (ms) |
|---|---|---|---|---|---|
| capsule.create | 5 | 61.3 | 136.3 | 136.3 | 75.6 |
| capsule.mediate | 20 | 0.008 | 0.033 | 0.033 | 0.010 |
| capsule.policy_evaluate | 20 | 0.010 | 0.050 | 0.050 | 0.013 |
| capsule.checkpoint | 5 | 2.94 | 4.27 | 4.27 | 3.16 |
| capsule.restore | 5 | 0.060 | 0.083 | 0.083 | 0.060 |
| capsule.replay_observe | 5 | 0.001 | 0.003 | 0.003 | 0.002 |

Isolation probes: filesystem 6/6 denied, network 4/4 blocked — PASS.
Unmeasured items: crash/restart recovery timing, remote migration, 1000-agent
scheduler stress, GPU quotas, long-run drift.

## Not implemented / unavailable (honest)

- GPU isolation (NOT_SUPPORTED)
- VM isolation (UNAVAILABLE in 1.0)
- Remote node migration (REQUIRES_CONFIGURATION — moves nothing)
- Long-run drift test (NOT_TESTED)
- Live AIAgent path (opt-in via AETHEROS_KERNEL_REAL_AGENT=1, untested)
- Cross-platform (Linux/macOS) - detection present but NOT_TESTED