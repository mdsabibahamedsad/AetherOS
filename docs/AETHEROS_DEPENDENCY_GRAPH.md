# AetherOS Dependency Graph

```text
kernel.core.types (no deps)
       ↑
kernel/event_bus, kernel/lifecycle (infra)
       ↑
core managers (config + event_bus + explicit manager refs:
  authority→policy+security; invoker→all; hypervisor→kernel)
       ↑
AgentKernel (constructs all; hypervisor last; shuts down hypervisor first)
       ↑
KernelSDK / CapsuleAPI / syscalls / CLI (facades only)
```

## Implementation Order (Master 59)

```
PHASE A: error taxonomy, intent envelope, verification honesty, model availability, task adapter, memory_os bridge, checkpoint linkage, IPC hardening, concurrency tests, benchmarks, docs
PHASE B: architecture docs, dependency graph, certification matrix, completion report
```

## Prohibited Dependencies (verified absent)

```
Model          → Policy bypass, Secret store, OS shell, Raw filesystem, Raw network, Electron IPC
Renderer       → Backend privileged APIs (only `aetherosDesktop.api` allowlist)
Agent          → Direct host filesystem (always via capsule FS)
Tool           → Direct host (always via CapabilityInvoker)
MCP Server     → Host credentials/kernel authority (grant-mediated)
Remote Agent   → Local privileged capabilities (pairing + trust required)
```

No circular imports: `import kernel.core` clean. Verified by import test.