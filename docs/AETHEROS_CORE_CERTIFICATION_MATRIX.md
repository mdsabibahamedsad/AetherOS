# AetherOS Core Certification Matrix

## Subsystems

| Subsystem | Implementation | Integration | Tests | Security | Performance | Documentation | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| Intent ABI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_intent_admission_and_validation`, `test_intent_envelope_*` |
| Task Model | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_import_graph_*` |
| Agent Process | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_agent_lifecycle_*`, `test_capsule_*` |
| Scheduler | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_capsule_*` (admit/schedule) |
| Capability Registry | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_capability_syscall_*`, `test_syscall_catalog_registers` |
| Policy/Authority | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_capsule_cannot_*`, `test_child_*` |
| Memory (kernel + 2.0) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_memory_os_bridge_*`, `test_memory_2_provider` |
| Model Runtime | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_unconfigured_models_not_selectable` |
| Tool Runtime | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_capability_syscall_*`, `test_syscall_catalog_*` |
| Event/Observability | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_*` (events emitted) |
| Verification | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_verification_honesty`, `test_replay_*` |
| Recovery/Checkpoint | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_snapshot_*`, `test_quarantine_*` |
| Capsule/Hypervisor | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_capsule_*` (all) |
| Security Boundary | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | 11× §111 invariants |
| Security Tests | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_agent_capsule_security.py` (54) |
| Concurrency Tests | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `test_concurrent_*`, `test_receipt_chain_*` |
| Benchmarks | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | `run_capsule_benchmarks` (real) |
| Documentation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | PASS | 14 architecture docs |
| Cross-platform | PARTIAL | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | PARTIAL | PARTIAL | Linux/macOS detection present, NOT_TESTED |
| GPU Isolation | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | `gpu_status()` → NOT_SUPPORTED |
| VM Isolation | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_IMPLEMENTED | UNAVAILABLE | VM provider UNAVAILABLE |
| Remote Migration | IMPLEMENTED | REQUIRES_CONFIGURATION | NOT_TESTED | NOT_TESTED | NOT_TESTED | IMPLEMENTED | BLOCKED | `migrate_capsule` → REQUIRES_CONFIGURATION |
| GPU Enforcement | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | `gpu_status()` → NOT_SUPPORTED |
| Long-run Drift | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | Procedure in test plan, not run |
| Live AIAgent | OPT-IN | UNTESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | DOCUMENTED | NOT_TESTED | Requires `AETHEROS_KERNEL_REAL_AGENT=1` |

## Status Legend

- **PASS**: Implemented, integrated, tested, documented, measured
- **PARTIAL**: Partially done, some gaps
- **NOT_IMPLEMENTED**: Not built
- **NOT_TESTED**: Exists but not verified in CI
- **BLOCKED**: Requires external dependency not met
- **NOT_IMPLEMENTED**: Honestly not built
- **UNAVAILABLE**: Explicitly not available in 1.0

## Overall

**PRODUCTION_READY_WITH_WARNINGS** — Core runtime complete, tested,
measured, documented. Warnings: desktop Capsule Center, remote/VM/GPU
backends, long-run validation remain future work.